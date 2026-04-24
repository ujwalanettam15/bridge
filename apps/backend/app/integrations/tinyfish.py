import os
from datetime import datetime

import httpx

from app.core.env import load_bridge_env

load_bridge_env()


TINYFISH_RUN_URL = "https://agent.tinyfish.ai/v1/automation/run"
PARENT_REVIEW_NOTICE = "Parent review is required before anything is submitted or sent."

DEFAULT_IEP_SOURCE_URLS = [
    "https://www.sfusd.edu/sped",
    "https://www.sfusd.edu/employees/teaching/special-education-services-employee-resources/special-education-assistive-technology-accessibility-resources",
    "https://www.cde.ca.gov/sp/se/sr/atexmpl.asp",
]

IEP_AGENT_STEPS = [
    "Monitoring confirmed communication history",
    "Opening school and AAC sources with TinyFish",
    "Extracting support requirements",
    "Drafting parent-review packet",
    "Awaiting approval",
]


def _demo_sources() -> list[dict]:
    now = datetime.utcnow().isoformat()
    return [
        {
            "title": "SFUSD Special Education",
            "url": DEFAULT_IEP_SOURCE_URLS[0],
            "extracted_fact": "Families can request support through the special education and IEP process.",
            "timestamp": now,
            "provider": "TinyFish demo-mode",
        },
        {
            "title": "SFUSD Assistive Technology / AAC Resources",
            "url": DEFAULT_IEP_SOURCE_URLS[1],
            "extracted_fact": "Assistive technology and AAC supports can help students access communication across routines.",
            "timestamp": now,
            "provider": "TinyFish demo-mode",
        },
        {
            "title": "California Assistive Technology Checklist",
            "url": DEFAULT_IEP_SOURCE_URLS[2],
            "extracted_fact": "Teams can consider the student's communication needs, environments, tools, and supports.",
            "timestamp": now,
            "provider": "TinyFish demo-mode",
        },
    ]


def build_iep_packet(name: str, school_district: str, pattern_summary: dict, sources: list[dict]) -> dict:
    subject = f"Request for AAC / Assistive Technology Review for {name}"
    body = (
        "Hello,\n\n"
        f"I am requesting that the IEP team consider AAC and assistive technology support for {name}. "
        "Over the past week, we documented repeated parent-confirmed communication moments during "
        "mealtime and transition routines, especially around water and help requests.\n\n"
        f"We would like to discuss whether {name} may benefit from consistent communication supports across "
        "school and home settings. Attached is a brief summary of confirmed communication patterns and "
        "source-backed next steps for review.\n\n"
        "Thank you."
    )
    rationale = (
        f"{name}'s confirmed communication pattern shows repeated access needs during daily routines. "
        "The attached sources support a parent-review request for AAC and assistive technology consideration."
    )
    parent_next_steps = [
        "Review the packet and confirm that the communication pattern summary is accurate.",
        f"Share the packet with {school_district or 'the school team'} only after parent approval.",
        "Bring the source cards and confirmed-event timeline to the next IEP or therapy conversation.",
    ]
    return {
        "subject": subject,
        "body": body,
        "rationale": rationale,
        "parent_next_steps": parent_next_steps,
        "source_count": len(sources),
    }


def _normalize_tinyfish_source(url: str, payload: dict) -> dict:
    result = payload.get("result") or payload.get("data") or payload
    extracted = ""
    if isinstance(result, dict):
        extracted = (
            result.get("extracted_fact")
            or result.get("summary")
            or result.get("text")
            or result.get("content")
            or str(result)
        )
        title = result.get("title") or payload.get("title") or url
    else:
        extracted = str(result)
        title = payload.get("title") or url
    return {
        "title": title,
        "url": url,
        "extracted_fact": extracted[:900],
        "timestamp": datetime.utcnow().isoformat(),
        "provider": "TinyFish",
    }


async def extract_iep_sources(source_urls: list[str] | None = None) -> tuple[list[dict], dict]:
    urls = source_urls or DEFAULT_IEP_SOURCE_URLS
    api_key = os.getenv("TINYFISH_API_KEY")
    if not api_key:
        return _demo_sources(), {
            "status": "demo_mode",
            "provider": "TinyFish",
            "message": "TinyFish key not configured; using source-grounded demo facts.",
        }

    sources = []
    failures = []
    goal = (
        "Extract one concise fact about AAC, assistive technology, special education, or IEP supports "
        "that would help a parent draft an AAC/assistive technology review request. Return source title "
        "and the extracted fact."
    )
    async with httpx.AsyncClient(timeout=90) as client:
        for url in urls:
            try:
                response = await client.post(
                    TINYFISH_RUN_URL,
                    headers={
                        "X-API-Key": api_key,
                        "Content-Type": "application/json",
                    },
                    json={"url": url, "goal": goal},
                )
                response.raise_for_status()
                sources.append(_normalize_tinyfish_source(url, response.json()))
            except Exception as exc:
                failures.append({"url": url, "error": str(exc)})

    if not sources:
        return _demo_sources(), {
            "status": "demo_mode",
            "provider": "TinyFish",
            "message": "TinyFish extraction failed; using fallback source facts for the demo.",
            "failures": failures,
        }

    return sources, {
        "status": "completed" if not failures else "partial",
        "provider": "TinyFish",
        "message": f"Extracted {len(sources)} source fact(s) with TinyFish.",
        "failures": failures,
    }


async def run_iep_agent(child_profile: dict, school_district: str, pattern_summary: dict, source_urls: list[str] | None = None):
    name = child_profile.get("name", "Maya")
    sources, tinyfish_status = await extract_iep_sources(source_urls)
    draft = build_iep_packet(name, school_district, pattern_summary, sources)
    return {
        "status": "source_grounded" if tinyfish_status["status"] != "demo_mode" else "demo_mode",
        "agent_steps": IEP_AGENT_STEPS,
        "sources": sources,
        "extracted_facts": [source["extracted_fact"] for source in sources],
        "draft": draft,
        "parent_control_notice": PARENT_REVIEW_NOTICE,
        "sponsor_statuses": {
            "tinyfish": tinyfish_status,
            "ghost": {
                "status": "configured_by_database_url",
                "provider": "Ghost/Postgres",
                "message": "Agent audit writes to the configured DATABASE_URL.",
            },
        },
    }


async def file_iep_request(child_profile: dict, school_district: str):
    return await run_iep_agent(child_profile, school_district, {})


async def appeal_insurance_denial(child_profile: dict, insurance_provider: str, denial_reason: str):
    name = child_profile.get("name", "your child")
    return {
        "status": "demo_mode",
        "message": f"Insurance appeal drafting is secondary for this demo. Prepared parent-review outline for {name}.",
        "agent_steps": ["Reading child profile", "Reviewing denial reason", "Preparing parent review"],
        "parent_control_notice": PARENT_REVIEW_NOTICE,
        "draft": {
            "subject": f"AAC coverage appeal for {name}",
            "body": (
                f"To the Appeals Team at {insurance_provider},\n\n"
                f"I am requesting review of the AAC coverage denial for {name}. "
                f"The denial reason listed was: {denial_reason}.\n\n"
                "Please reconsider based on functional communication need and supporting clinical documentation.\n\n"
                "Sincerely,\nParent/Guardian"
            ),
            "rationale": "Secondary demo-mode appeal draft. Main hackathon flow is the source-grounded IEP packet.",
            "parent_next_steps": ["Review insurer denial notice.", "Attach clinical documentation.", "Submit only after parent approval."],
        },
    }


async def search_therapists(child_profile: dict, zip_code: str, insurance_provider: str = ""):
    return {
        "status": "demo_mode",
        "message": f"Therapist matching is secondary for this demo. Showing prepared AAC provider examples near {zip_code}.",
        "agent_steps": ["Reading child profile", "Searching therapist directories", "Preparing parent review"],
        "parent_control_notice": "Parent review is required before outreach.",
        "resources": [
            {
                "name": "Dr. Jane Smith, CCC-SLP",
                "specialty": "AAC and complex communication needs",
                "distance": "2.3 mi",
                "insurance": ["BCBS", "Aetna"],
            },
            {
                "name": "Michael Torres, MS, SLP",
                "specialty": "AAC, autism, early intervention",
                "distance": "4.1 mi",
                "insurance": ["United", "Medicaid"],
            },
        ],
    }
