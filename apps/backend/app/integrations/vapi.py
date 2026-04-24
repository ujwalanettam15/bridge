import httpx
import os

from app.core.env import load_bridge_env

load_bridge_env()

VAPI_BASE = "https://api.vapi.ai"


async def speak_symbol(phrase: str, child_voice_id: str = None):
    if not os.getenv("VAPI_API_KEY"):
        return {
            "status": "demo_mode",
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
    customer_number = (call_config or {}).get("customer_number") or os.getenv("VAPI_CUSTOMER_NUMBER")

    if not api_key or not phone_number_id or not customer_number:
        return {
            "status": "demo_mode",
            "provider": "Vapi",
            "message": "Vapi call config is missing; prepared parent-approved care-team voice update payload.",
            "voice_update": summary_text,
            "required_env": ["VAPI_API_KEY", "VAPI_PHONE_NUMBER_ID", "VAPI_CUSTOMER_NUMBER"],
        }

    payload = {
        "phoneNumberId": phone_number_id,
        "customer": {"number": customer_number},
        "assistant": {
            "firstMessage": summary_text,
            "endCallAfterSilence": 8,
        },
    }
    if assistant_id:
        payload = {
            "phoneNumberId": phone_number_id,
            "customer": {"number": customer_number},
            "assistantId": assistant_id,
            "assistantOverrides": {"firstMessage": summary_text},
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
                "vapi_response": response.json() if response.content else {},
            }
    except httpx.HTTPStatusError as exc:
        return {
            "status": "error",
            "provider": "Vapi",
            "message": f"Vapi returned HTTP {exc.response.status_code}; voice update payload is prepared.",
            "voice_update": summary_text,
        }
    except Exception:
        return {
            "status": "error",
            "provider": "Vapi",
            "message": "Could not reach Vapi; voice update payload is prepared.",
            "voice_update": summary_text,
        }
