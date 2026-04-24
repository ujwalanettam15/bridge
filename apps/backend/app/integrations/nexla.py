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


async def sync_therapist_summary_to_nexla(summary_data: dict, therapist_webhook: str = "") -> dict:
    nexla_api_key = os.getenv("NEXLA_API_KEY")
    nexla_flow_id = os.getenv("NEXLA_FLOW_ID")

    if not nexla_api_key or not nexla_flow_id:
        return {
            "status": "demo_mode",
            "provider": "Nexla",
            "message": (
                "Nexla is not configured. In a live deployment, this summary would be "
                "routed automatically to your therapist's inbox or EHR via a Nexla data flow — "
                "no manual copy-paste required."
            ),
            "summary_available": True,
            "summary": summary_data,
            "next_steps": [
                "Add NEXLA_API_KEY and NEXLA_FLOW_ID to your .env file",
                "Configure a Nexla flow to deliver summaries to your therapist's preferred destination",
                "Summaries will sync automatically on each generation once keys are set",
            ],
        }

    try:
        async with httpx.AsyncClient(timeout=15.0) as http_client:
            response = await http_client.post(
                f"https://api.nexla.io/v1/flows/{nexla_flow_id}/trigger",
                headers={
                    "Authorization": f"Bearer {nexla_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "data": summary_data,
                    "destination": therapist_webhook,
                    "type": "therapist_summary",
                },
            )
            response.raise_for_status()
            return {
                "status": "synced",
                "provider": "Nexla",
                "message": f"Therapist summary for {summary_data.get('child_name', 'child')} sent via Nexla.",
                "nexla_response": response.json() if response.content else {},
            }
    except httpx.HTTPStatusError as exc:
        return {
            "status": "error",
            "provider": "Nexla",
            "message": f"Nexla returned HTTP {exc.response.status_code}. Summary is available locally.",
            "summary_available": True,
            "summary": summary_data,
        }
    except Exception:
        return {
            "status": "error",
            "provider": "Nexla",
            "message": "Could not reach Nexla. Summary is available locally and can be shared manually.",
            "summary_available": True,
            "summary": summary_data,
        }
