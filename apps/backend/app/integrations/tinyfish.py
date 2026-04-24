import httpx
import os


async def file_iep_request(child_profile: dict, school_district: str):
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            "https://api.tinyfish.ai/v1/agent/run",
            headers={"Authorization": f"Bearer {os.getenv('TINYFISH_API_KEY')}"},
            json={
                "task": f"Navigate to {school_district} school district IEP portal and submit an AAC device request for a student",
                "context": {
                    "child_name": child_profile["name"],
                    "child_age": child_profile["age"],
                    "disability_category": "Autism Spectrum Disorder",
                    "requested_device": "AAC Communication Device",
                    "justification": "Non-verbal student requires AAC device for educational participation",
                },
                "return_when": "form_submitted",
            },
        )
    return response.json()


async def appeal_insurance_denial(child_profile: dict, insurance_provider: str, denial_reason: str):
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            "https://api.tinyfish.ai/v1/agent/run",
            headers={"Authorization": f"Bearer {os.getenv('TINYFISH_API_KEY')}"},
            json={
                "task": f"Navigate to {insurance_provider} member portal and file an appeal for denied AAC device coverage",
                "context": child_profile,
                "denial_reason": denial_reason,
            },
        )
    return response.json()
