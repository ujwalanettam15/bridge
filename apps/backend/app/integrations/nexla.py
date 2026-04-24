import httpx
import os


async def sync_session_to_therapist(session_data: dict, therapist_webhook: str):
    async with httpx.AsyncClient() as client:
        await client.post(
            f"https://api.nexla.io/v1/flows/{os.getenv('NEXLA_FLOW_ID')}/trigger",
            headers={"Authorization": f"Bearer {os.getenv('NEXLA_API_KEY')}"},
            json={
                "data": session_data,
                "destination": therapist_webhook,
            },
        )
