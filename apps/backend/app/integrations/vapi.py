import httpx
import os
import re

from app.core.env import load_bridge_env

load_bridge_env()

VAPI_BASE = "https://api.vapi.ai"


def _redact(value: str | None) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}...{value[-4:]}"


def _valid_e164(number: str | None) -> bool:
    return bool(number and re.fullmatch(r"\+[1-9]\d{7,14}", number.strip()))


def _call_variable_values(summary_text: str) -> dict:
    return {
        "child_name": "Maya",
        "confirmed_moments": "15",
        "top_intents": "hat comfort requests, water, help, more, break, stop, and too-loud moments",
        "common_contexts": "meals, school drop-off, transitions, lunch, therapy, bedtime, and homework",
        "packet_status": "AAC and assistive technology support packet prepared for parent review",
        "parent_next_step": "review the evidence packet with the school or care team",
        "care_update": summary_text,
    }


def _prepared_call_payload(
    summary_text: str,
    phone_number_id: str | None,
    customer_number: str | None,
    assistant_id: str | None,
    variable_values: dict | None = None,
    metadata: dict | None = None,
    include_server_url: bool = False,
) -> dict:
    payload = {
        "phoneNumberId": phone_number_id or "set VAPI_PHONE_NUMBER_ID",
        "customer": {"number": customer_number or "set VAPI_CUSTOMER_NUMBER"},
    }
    if metadata:
        payload["metadata"] = metadata
    if assistant_id:
        payload["assistantId"] = assistant_id
        payload["assistantOverrides"] = {
            "variableValues": variable_values or _call_variable_values(summary_text),
        }
        server_url = os.getenv("VAPI_SERVER_URL") if include_server_url else ""
        if server_url:
            payload["assistantOverrides"]["server"] = {"url": server_url}
            payload["assistantOverrides"]["serverMessages"] = [
                "status-update",
                "transcript",
                "end-of-call-report",
                "conversation-update",
            ]
    else:
        payload["assistant"] = {
            "name": "Bridge Care Team Update",
            "firstMessage": summary_text,
            "firstMessageMode": "assistant-speaks-first",
            "model": {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are Bridge, a parent-approved care-team update assistant. "
                            "Read the care update clearly, answer only basic clarification questions, "
                            "and do not diagnose or provide medical advice."
                        ),
                    }
                ],
            },
            "voice": {"provider": "vapi", "voiceId": "Elliot"},
        }
    return payload


async def speak_symbol(phrase: str, child_voice_id: str = None):
    if not os.getenv("VAPI_API_KEY"):
        return {
            "status": "prepared",
            "message": "Browser speech synthesis handled local AAC playback. Vapi is reserved for care-team voice updates.",
            "phrase": phrase,
        }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{VAPI_BASE}/call/web",
            headers={"Authorization": f"Bearer {os.getenv('VAPI_API_KEY')}"},
            json={
                "assistant": {
                    "voice": {
                        "provider": "11labs",
                        "voiceId": child_voice_id or "child-default",
                    },
                    "firstMessage": phrase,
                    "endCallAfterSilence": 3,
                }
            },
        )
    return response.json()


async def send_care_team_voice_update(summary_text: str, call_config: dict | None = None):
    api_key = os.getenv("VAPI_API_KEY")
    phone_number_id = os.getenv("VAPI_PHONE_NUMBER_ID")
    assistant_id = os.getenv("VAPI_ASSISTANT_ID")
    customer_number = ((call_config or {}).get("customer_number") or os.getenv("VAPI_CUSTOMER_NUMBER") or "").strip()
    payload = _prepared_call_payload(summary_text, phone_number_id, customer_number, assistant_id)

    if not api_key or not phone_number_id or not customer_number:
        missing = [
            name for name, value in {
                "VAPI_API_KEY": api_key,
                "VAPI_PHONE_NUMBER_ID": phone_number_id,
                "VAPI_CUSTOMER_NUMBER": customer_number,
            }.items()
            if not value
        ]
        return {
            "status": "prepared",
            "provider": "Vapi",
            "message": "Care-team voice update payload prepared. Add the missing Vapi call config to start the live call.",
            "voice_update": summary_text,
            "missing_config": missing,
            "call_payload": payload,
        }

    if not _valid_e164(customer_number):
        return {
            "status": "prepared",
            "provider": "Vapi",
            "message": "Vapi payload is ready, but the customer number must be E.164 format like +14155551234.",
            "voice_update": summary_text,
            "call_payload": payload,
            "config_check": {
                "phoneNumberId": _redact(phone_number_id),
                "customer_number": customer_number,
                "assistant": "configured" if assistant_id else "inline assistant",
            },
        }

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{VAPI_BASE}/call",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            return {
                "status": "started",
                "provider": "Vapi",
                "message": "Care-team voice update started with Vapi.",
                "call_payload": payload,
                "vapi_response": response.json() if response.content else {},
            }
    except httpx.HTTPStatusError as exc:
        try:
            error_detail = exc.response.json()
        except Exception:
            error_detail = exc.response.text[:1000]
        return {
            "status": "prepared",
            "provider": "Vapi",
            "message": f"Vapi rejected the call request with HTTP {exc.response.status_code}. Payload is ready; check the Vapi config IDs and customer number.",
            "voice_update": summary_text,
            "call_payload": payload,
            "vapi_error": error_detail,
            "config_check": {
                "phoneNumberId": _redact(phone_number_id),
                "customer_number": customer_number,
                "assistant": "configured" if assistant_id else "inline assistant",
            },
        }
    except Exception:
        return {
            "status": "prepared",
            "provider": "Vapi",
            "message": "Could not reach Vapi; care-team voice update payload is prepared.",
            "voice_update": summary_text,
            "call_payload": payload,
        }


async def request_teacher_daily_update(
    child_name: str,
    teacher_contact: dict,
    evidence_summary: dict,
    requested_questions: list[str],
    agent_run_id: str,
):
    api_key = os.getenv("VAPI_API_KEY")
    phone_number_id = os.getenv("VAPI_PHONE_NUMBER_ID")
    assistant_id = os.getenv("VAPI_TEACHER_ASSISTANT_ID") or os.getenv("VAPI_ASSISTANT_ID")
    customer_number = (teacher_contact.get("phone") or os.getenv("VAPI_CUSTOMER_NUMBER") or "").strip()
    teacher_name = teacher_contact.get("name") or "teacher"
    summary_text = (
        f"Hi {teacher_name}, this is Bridge calling with parent approval for {child_name}. "
        "Please share today's communication update, what supports helped, any friction points, "
        "and one recommended home follow-up."
    )
    variable_values = {
        "child_name": child_name,
        "teacher_name": teacher_name,
        "teacher_role": teacher_contact.get("role") or "teacher",
        "agent_run_id": agent_run_id,
        "today_evidence_summary": evidence_summary,
        "requested_update_questions": requested_questions,
        "callback_context": "teacher_daily_update",
    }
    payload = _prepared_call_payload(
        summary_text,
        phone_number_id,
        customer_number,
        assistant_id,
        variable_values=variable_values,
        metadata={
            "bridge_agent_run_id": agent_run_id,
            "bridge_action_type": "teacher_daily_update",
            "child_name": child_name,
        },
        include_server_url=True,
    )

    if not api_key or not phone_number_id or not customer_number or not assistant_id:
        missing = [
            name for name, value in {
                "VAPI_API_KEY": api_key,
                "VAPI_PHONE_NUMBER_ID": phone_number_id,
                "VAPI_CUSTOMER_NUMBER/teacher phone": customer_number,
                "VAPI_TEACHER_ASSISTANT_ID or VAPI_ASSISTANT_ID": assistant_id,
            }.items()
            if not value
        ]
        return {
            "status": "prepared",
            "provider": "Vapi",
            "message": "Teacher update call payload prepared. Add the missing Vapi call config to start the live call.",
            "missing_config": missing,
            "call_payload": payload,
        }

    if not _valid_e164(customer_number):
        return {
            "status": "prepared",
            "provider": "Vapi",
            "message": "Teacher update payload is ready, but the teacher/customer number must be E.164 format like +14155551234.",
            "call_payload": payload,
            "config_check": {
                "phoneNumberId": _redact(phone_number_id),
                "customer_number": customer_number,
                "assistant": _redact(assistant_id),
            },
        }

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{VAPI_BASE}/call",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            data = response.json() if response.content else {}
            return {
                "status": data.get("status") or "queued",
                "provider": "Vapi",
                "message": "Teacher update call queued with Vapi.",
                "call_id": data.get("id"),
                "call_payload": payload,
                "vapi_response": data,
            }
    except httpx.HTTPStatusError as exc:
        try:
            error_detail = exc.response.json()
        except Exception:
            error_detail = exc.response.text[:1000]
        return {
            "status": "prepared",
            "provider": "Vapi",
            "message": f"Vapi returned HTTP {exc.response.status_code}; teacher update payload is prepared.",
            "call_payload": payload,
            "vapi_error": error_detail,
            "config_check": {
                "phoneNumberId": _redact(phone_number_id),
                "customer_number": customer_number,
                "assistant": _redact(assistant_id),
            },
        }
    except Exception:
        return {
            "status": "prepared",
            "provider": "Vapi",
            "message": "Could not reach Vapi; teacher update call payload is prepared.",
            "call_payload": payload,
        }
