import httpx
import os

VAPI_BASE = "https://api.vapi.ai"


async def speak_symbol(phrase: str, child_voice_id: str = None):
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
