"""
Ghost / TigerData integration for Bridge.

Ghost provides:
  1. The managed Postgres database (via DATABASE_URL).
  2. A durable DB-backed event queue for agent stage events.
  3. Database forking — the Care Agent forks the DB before a run, drafts safely, then cleans up.
  4. Space status API — surfaced in the sponsor audit panel.
"""

import asyncio
import json
import logging
import os
from functools import lru_cache

import httpx
from sqlalchemy import text

from app.core.database import engine
from app.core.env import load_bridge_env

logger = logging.getLogger(__name__)

GHOST_API_BASE = "https://api.ghost.build/v1"

_QUEUES = ["bridge_agent_events", "bridge_care_actions"]
_QUEUE_TABLE = "bridge_queue_messages"


@lru_cache(maxsize=1)
def _ensure_ghost_env_loaded() -> None:
    # Make Ghost env access safe even if this module is imported before app startup.
    load_bridge_env()


def _api_key() -> str:
    _ensure_ghost_env_loaded()
    return os.getenv("GHOST_API_KEY", "")


def _db_name() -> str:
    _ensure_ghost_env_loaded()
    return os.getenv("GHOST_DATABASE_NAME", "bridge-prod")


def _queue_timestamp_sql() -> str:
    return "NOW()" if engine.dialect.name == "postgresql" else "CURRENT_TIMESTAMP"


def _validate_queue_name(queue: str) -> bool:
    if queue in _QUEUES:
        return True
    logger.warning("Unknown Ghost queue requested: %s", queue)
    return False


def _decode_message(raw: object) -> dict:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"raw": raw}
    return {"raw": raw}


# Startup initialisation

def init_pgmq() -> None:
    """
    Create the durable Ghost queue table used for event reads.
    Called once at app startup via main.py on_startup.
    """
    try:
        with engine.begin() as conn:
            if engine.dialect.name == "postgresql":
                conn.execute(
                    text(
                        f"""
                        CREATE TABLE IF NOT EXISTS {_QUEUE_TABLE} (
                            id BIGSERIAL PRIMARY KEY,
                            queue_name TEXT NOT NULL,
                            message TEXT NOT NULL,
                            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                            archived_at TIMESTAMPTZ NULL
                        )
                        """
                    )
                )
            else:
                conn.execute(
                    text(
                        f"""
                        CREATE TABLE IF NOT EXISTS {_QUEUE_TABLE} (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            queue_name TEXT NOT NULL,
                            message TEXT NOT NULL,
                            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                            archived_at TEXT NULL
                        )
                        """
                    )
                )
            conn.execute(
                text(
                    f"""
                    CREATE INDEX IF NOT EXISTS ix_{_QUEUE_TABLE}_pending
                    ON {_QUEUE_TABLE} (queue_name, archived_at, id)
                    """
                )
            )
        logger.info("Ghost queue storage ready: %s", ", ".join(_QUEUES))
    except Exception as exc:
        logger.warning("Ghost queue init failed: %s", exc)


# Space / status

async def get_ghost_status() -> dict:
    """
    Call Ghost REST API to get space usage info.
    Falls back gracefully when GHOST_API_KEY is absent (demo-mode).
    """
    api_key = _api_key()
    db_name = _db_name()

    if not api_key:
        return {
            "status": "demo_mode",
            "message": "GHOST_API_KEY not configured — using local Postgres fallback",
            "database": db_name,
            "features": ["db_queue", "audit_store", "database_fork"],
        }

    async def status_via_cli() -> dict:
        proc = await asyncio.create_subprocess_exec(
            "ghost",
            "status",
            "--json",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(stderr.decode().strip() or "ghost status failed")
        data = json.loads(stdout.decode())
        return {
            "status": "connected",
            "database": db_name,
            "compute_hours_used": round((data.get("compute_minutes") or 0) / 60, 2),
            "compute_hours_limit": round((data.get("compute_limit_minutes") or 0) / 60, 2),
            "storage_bytes": int((data.get("storage_mib") or 0) * 1024 * 1024),
            "features": ["db_queue", "audit_store", "database_fork"],
            "raw": data,
        }

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(
                f"{GHOST_API_BASE}/spaces/status",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            r.raise_for_status()
            data = r.json()
            return {
                "status": "connected",
                "database": db_name,
                "compute_hours_used": data.get("compute_hours_used"),
                "compute_hours_limit": data.get("compute_hours_limit"),
                "storage_bytes": data.get("storage_bytes"),
                "features": ["db_queue", "audit_store", "database_fork"],
                "raw": data,
            }
    except Exception as exc:
        logger.warning("Ghost REST status check failed: %s", exc)
        try:
            return await status_via_cli()
        except Exception as cli_exc:
            logger.warning("Ghost CLI status check failed: %s", cli_exc)
            return {"status": "error", "message": str(cli_exc), "database": db_name}


# Durable event queue

def pgmq_send(queue: str, payload: dict) -> bool:
    """
    Compatibility wrapper for the app's queue publish calls.
    Persists JSON messages into a Ghost-backed queue table.
    """
    if not _validate_queue_name(queue):
        return False
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    f"""
                    INSERT INTO {_QUEUE_TABLE} (queue_name, message)
                    VALUES (:queue, :msg)
                    """
                ),
                {"queue": queue, "msg": json.dumps(payload)},
            )
        return True
    except Exception as exc:
        logger.warning("pgmq_send failed (queue=%s): %s", queue, exc)
        return False


def pgmq_read(queue: str, limit: int = 20) -> list[dict]:
    """
    Compatibility wrapper for the app's queue read calls.
    Reads and immediately archives messages from the Ghost-backed queue table.
    Returns message payloads as Python dicts.
    """
    if not _validate_queue_name(queue):
        return []
    try:
        with engine.begin() as conn:
            if engine.dialect.name == "postgresql":
                rows = conn.execute(
                    text(
                        f"""
                        WITH next_messages AS (
                            SELECT id
                            FROM {_QUEUE_TABLE}
                            WHERE queue_name = :queue
                              AND archived_at IS NULL
                            ORDER BY id
                            FOR UPDATE SKIP LOCKED
                            LIMIT :limit
                        )
                        UPDATE {_QUEUE_TABLE} AS queued
                        SET archived_at = NOW()
                        FROM next_messages
                        WHERE queued.id = next_messages.id
                        RETURNING queued.message
                        """
                    ),
                    {"queue": queue, "limit": limit},
                ).fetchall()
                return [_decode_message(r[0]) for r in rows]

            rows = conn.execute(
                text(
                    f"""
                    SELECT id, message
                    FROM {_QUEUE_TABLE}
                    WHERE queue_name = :queue
                      AND archived_at IS NULL
                    ORDER BY id
                    LIMIT :limit
                    """
                ),
                {"queue": queue, "limit": limit},
            ).fetchall()
            if not rows:
                return []

            id_list = ",".join(str(r[0]) for r in rows)
            conn.execute(
                text(
                    f"""
                    UPDATE {_QUEUE_TABLE}
                    SET archived_at = {_queue_timestamp_sql()}
                    WHERE id IN ({id_list})
                    """
                )
            )
            return [_decode_message(r[1]) for r in rows]
    except Exception as exc:
        logger.warning("pgmq_read failed (queue=%s): %s", queue, exc)
        return []


# Fork-for-agent-run

async def _fork_via_rest(run_label: str) -> dict:
    """Attempt fork via Ghost REST API."""
    api_key = _api_key()
    db_name = _db_name()
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(
            f"{GHOST_API_BASE}/databases/{db_name}/fork",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"name": f"bridge-agent-{run_label}"},
        )
        r.raise_for_status()
        data = r.json()
        return {
            "status": "created",
            "method": "rest",
            "fork_id": data.get("id"),
            "fork_name": data.get("name"),
            "connection_string": data.get("connection_string"),
        }


async def _fork_via_cli(run_label: str) -> dict:
    """Fallback: fork via ghost CLI subprocess."""
    db_name = _db_name()
    fork_name = f"bridge-agent-{run_label}"
    try:
        proc = await asyncio.create_subprocess_exec(
            "ghost",
            "fork",
            db_name,
            "--name",
            fork_name,
            "--wait",
            "--json",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("ghost CLI not installed or not on PATH") from exc
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(stderr.decode())
    data = json.loads(stdout.decode())
    return {
        "status": "created",
        "method": "cli",
        "fork_id": data.get("id"),
        "fork_name": fork_name,
        "connection_string": data.get("connection_string"),
    }


async def fork_for_agent_run(run_label: str) -> dict:
    """
    Fork the production Ghost database before a Care Agent run.
    The agent drafts on the fork; if the run succeeds, the fork is deleted.
    If something goes wrong, the fork is preserved for inspection.
    Tries REST API first, falls back to CLI, skips gracefully with no key.
    """
    if not _api_key():
        return {"status": "skipped", "reason": "GHOST_API_KEY not set"}
    try:
        return await _fork_via_rest(run_label)
    except Exception as rest_exc:
        logger.warning("Ghost REST fork failed (%s), trying CLI fallback", rest_exc)
        try:
            return await _fork_via_cli(run_label)
        except Exception as cli_exc:
            logger.warning("Ghost CLI fork also failed: %s", cli_exc)
            return {"status": "skipped", "reason": str(cli_exc)}


async def delete_fork(fork_name: str) -> bool:
    """Delete a previously created agent fork."""
    api_key = _api_key()
    if not api_key:
        return False
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.delete(
                f"{GHOST_API_BASE}/databases/{fork_name}",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            return r.status_code in (200, 204)
    except Exception as exc:
        logger.warning("Ghost fork delete failed (%s): %s", fork_name, exc)
        return False
