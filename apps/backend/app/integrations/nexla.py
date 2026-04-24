import httpx
import os

from app.core.env import load_bridge_env

load_bridge_env()


def _nexla_config_status() -> dict:
    webhook_url = os.getenv("NEXLA_INCOMING_WEBHOOK_URL")
    mcp_url = os.getenv("NEXLA_EXPRESS_MCP_URL", "https://veda-ai.nexla.io/mcp-express/")
    return {
        "webhook_configured": bool(webhook_url),
        "mcp_url": mcp_url,
        "express_steps": [
            "Create an Incoming Webhook source in Nexla Express",
            "Let Nexla generate the source Nexset",
            "Optionally add transforms and a data contract",
            "Deliver the approved packet to the configured target",
        ],
    }


async def _post_to_nexla_incoming_webhook(payload: dict) -> dict:
    webhook_url = os.getenv("NEXLA_INCOMING_WEBHOOK_URL")
    if not webhook_url:
        return {
            "status": "prepared",
            "provider": "Nexla Express",
            "message": "Nexla Incoming Webhook is not configured. Prepared the structured payload for Nexla Express.",
            "payload_available": True,
            "payload": payload,
            **_nexla_config_status(),
        }

    try:
        async with httpx.AsyncClient(timeout=20.0) as http_client:
            response = await http_client.post(
                webhook_url,
                headers={"Content-Type": "application/json"},
                json=payload,
            )
            response.raise_for_status()
            return {
                "status": "delivered",
                "provider": "Nexla Express",
                "message": "Parent-approved packet delivered to Nexla Incoming Webhook.",
                "nexla_response": response.json() if response.content else {},
                **_nexla_config_status(),
            }
    except httpx.HTTPStatusError as exc:
        return {
            "status": "error",
            "provider": "Nexla Express",
            "message": f"Nexla Incoming Webhook returned HTTP {exc.response.status_code}. Packet is saved in Bridge audit.",
            "payload_available": True,
            "payload": payload,
            **_nexla_config_status(),
        }
    except Exception:
        return {
            "status": "error",
            "provider": "Nexla Express",
            "message": "Could not reach the Nexla Incoming Webhook. Packet is saved in Bridge audit.",
            "payload_available": True,
            "payload": payload,
            **_nexla_config_status(),
        }


async def sync_session_to_therapist(session_data: dict, therapist_webhook: str):
    return await _post_to_nexla_incoming_webhook({
        "type": "session_data",
        "destination_hint": therapist_webhook,
        "data": session_data,
    })


async def sync_therapist_summary_to_nexla(summary_data: dict, therapist_webhook: str = "") -> dict:
    return await _post_to_nexla_incoming_webhook({
        "type": "therapist_summary",
        "destination_hint": therapist_webhook,
        "data": summary_data,
    })


async def sync_care_packet_to_nexla(packet_data: dict, therapist_webhook: str = "") -> dict:
    return await _post_to_nexla_incoming_webhook({
        "type": "aac_iep_support_packet",
        "destination_hint": therapist_webhook,
        "data": packet_data,
    })


async def sync_teacher_update_to_nexla(update_data: dict, destination_hint: str = "") -> dict:
    return await _post_to_nexla_incoming_webhook({
        "type": "teacher_daily_update",
        "destination_hint": destination_hint,
        "data": update_data,
    })
