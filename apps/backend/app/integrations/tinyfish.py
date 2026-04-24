import httpx
import os


async def file_iep_request(child_profile: dict, school_district: str):
    if not os.getenv("TINYFISH_API_KEY"):
        return {
            "status": "demo_mode",
            "message": "TinyFish API key not configured; generated a parent-review IEP request draft.",
            "steps": [
                "Read child profile",
                f"Prepared AAC support request for {school_district}",
                "Queued parent review before submission",
            ],
            "result": (
                f"Draft IEP request for {child_profile['name']}: request an AAC evaluation, "
                "communication accommodations, and assistive technology support."
            ),
        }

    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            "https://api.tinyfish.ai/v1/agent/run",
            headers={"Authorization": f"Bearer {os.getenv('TINYFISH_API_KEY')}"},
            json={
                "task": f"Navigate to {school_district} school district IEP portal and submit an AAC device request for a student",
                "context": {
                    "child_name": child_profile["name"],
                    "child_age": child_profile["age"],
                    "grade": child_profile.get("grade", ""),
                    "disability_category": child_profile.get("disability_category") or "Autism Spectrum Disorder",
                    "requested_device": "AAC Communication Device",
                    "justification": "Non-verbal student requires AAC device for educational participation",
                },
                "return_when": "form_submitted",
            },
        )
    return response.json()


async def appeal_insurance_denial(child_profile: dict, insurance_provider: str, denial_reason: str):
    if not os.getenv("TINYFISH_API_KEY"):
        return {
            "status": "demo_mode",
            "message": "TinyFish API key not configured; generated a parent-review appeal draft.",
            "steps": [
                "Read child profile",
                f"Prepared appeal packet for {insurance_provider}",
                "Queued parent review before submission",
            ],
            "result": (
                f"Draft appeal for {child_profile['name']}: explain AAC medical necessity, "
                f"address denial reason '{denial_reason}', and attach provider documentation."
            ),
        }

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
