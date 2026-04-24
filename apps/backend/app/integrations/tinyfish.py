import os

import httpx


IEP_AGENT_STEPS = [
    "Reading child profile",
    "Drafting request",
    "Searching district portal",
    "Preparing parent review",
]

APPEAL_AGENT_STEPS = [
    "Reading child profile",
    "Drafting request",
    "Reviewing insurer requirements",
    "Preparing parent review",
]

THERAPIST_AGENT_STEPS = [
    "Reading child profile",
    "Searching therapist directories",
    "Filtering AAC matches",
    "Preparing parent review",
]

PARENT_REVIEW_NOTICE = "Parent review is required before anything is submitted or sent."


def _normalize_agent_response(payload: dict, fallback_message: str, agent_steps: list[str]) -> dict:
    payload = payload or {}
    raw_steps = payload.get("agent_steps") or payload.get("steps") or agent_steps
    normalized_steps = []
    for step in raw_steps:
        if isinstance(step, str):
            normalized_steps.append(step)
        else:
            normalized_steps.append(step.get("description", "Processing agent step"))

    payload["agent_steps"] = normalized_steps
    payload.setdefault("message", fallback_message)
    payload.setdefault("parent_control_notice", PARENT_REVIEW_NOTICE)
    return payload


def _iep_demo_payload(name: str, school_district: str, grade: str, disability: str) -> dict:
    grade_suffix = f" ({grade})" if grade else ""
    subject = f"Request for IEP evaluation and AAC supports for {name}{grade_suffix}"
    body = (
        f"Dear {school_district} Special Education Team,\n\n"
        f"I am writing to request an initial IEP evaluation and AAC-related supports for my child, "
        f"{name}{grade_suffix}. {name} has a disability classification of {disability} and uses "
        "augmentative and alternative communication (AAC) to express needs, participate in instruction, "
        "and engage safely across school settings.\n\n"
        "I am requesting:\n"
        "1. A comprehensive speech-language evaluation that includes AAC access and communication needs\n"
        "2. A review of classroom accommodations and staff supports that would help AAC use during instruction\n"
        "3. An assistive technology evaluation to determine appropriate AAC tools and implementation needs\n"
        "4. A meeting to discuss evaluation timelines, communication goals, and next steps for services\n\n"
        "Please confirm receipt of this request in writing and let me know the next step in your district's "
        "evaluation process. I appreciate your partnership in supporting my child's communication access at school.\n\n"
        f"Sincerely,\n{name}'s Parent/Guardian"
    )
    rationale = (
        f"This draft ties {name}'s AAC needs to school access, participation, and evaluation rights under IDEA. "
        f"Naming {disability} and the request for AAC-specific evaluation helps the district route the request to "
        "the right team while keeping the language collaborative and parent-led."
    )
    parent_next_steps = [
        f"Review the draft and confirm that {name}'s grade and disability category are correct.",
        f"Send it to {school_district}'s special education office or upload it to the district portal yourself.",
        "Keep a dated copy of the request and any district confirmation.",
        "Ask for the district's written evaluation timeline and meeting process in the same thread.",
    ]
    return {
        "status": "demo_mode",
        "message": (
            f"IEP review packet prepared for {name}. Review it before you send anything to {school_district}."
        ),
        "agent_steps": IEP_AGENT_STEPS,
        "parent_control_notice": PARENT_REVIEW_NOTICE,
        "draft": {
            "subject": subject,
            "body": body,
            "rationale": rationale,
            "parent_next_steps": parent_next_steps,
        },
    }


def _appeal_demo_payload(name: str, insurance_provider: str, denial_reason: str) -> dict:
    subject = f"AAC coverage appeal for {name}"
    body = (
        f"To the Appeals Team at {insurance_provider},\n\n"
        f"I am requesting a review of the denial for AAC device coverage for my child, {name}. "
        f"The denial reason listed was: {denial_reason}.\n\n"
        f"My child relies on AAC to communicate needs, participate in school and community settings, and reduce "
        "health and safety risks caused by communication barriers. For that reason, the requested device is "
        "medically necessary, not optional convenience equipment.\n\n"
        "Please reconsider this denial based on the prescribing clinician's recommendation, the speech-language "
        "evaluation, and the documented need for AAC access across daily environments. I am asking for a written "
        "response explaining the outcome of this appeal and any additional documentation required.\n\n"
        f"Sincerely,\n{name}'s Parent/Guardian"
    )
    rationale = (
        "The draft centers medical necessity, functional impact, and the need for supporting documentation. "
        "That combination is usually stronger than simply disputing the denial reason by itself."
    )
    parent_next_steps = [
        "Review the denial reason and confirm the draft matches the insurer's notice.",
        "Attach the AAC evaluation and clinician letter of medical necessity before sending.",
        f"Submit the appeal through {insurance_provider}'s parent-facing channel yourself.",
        "Save a copy of everything you submit and note the response deadline on the denial letter.",
    ]
    return {
        "status": "demo_mode",
        "message": (
            f"Appeal review packet prepared for {name}. Review it before you send anything to {insurance_provider}."
        ),
        "agent_steps": APPEAL_AGENT_STEPS,
        "parent_control_notice": PARENT_REVIEW_NOTICE,
        "draft": {
            "subject": subject,
            "body": body,
            "rationale": rationale,
            "parent_next_steps": parent_next_steps,
        },
    }


def _therapist_demo_payload(zip_code: str, insurance_provider: str = "") -> dict:
    insurance_note = insurance_provider or "parent insurance preferences"
    return {
        "status": "demo_mode",
        "message": (
            f"Demo therapist matches prepared for ZIP {zip_code}. Review details before contacting providers."
        ),
        "agent_steps": THERAPIST_AGENT_STEPS,
        "parent_control_notice": "Bridge is showing draft resource matches only. Parent review is required before outreach.",
        "resource_mode": "demo",
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
            {
                "name": "Sarah Lee, PhD, CCC-SLP",
                "specialty": "Complex communication needs and AAC implementation",
                "distance": "5.8 mi",
                "insurance": ["BCBS", "Cigna"],
            },
        ],
        "resource_note": (
            f"Demo mode only. In a live TinyFish flow, the agent would compile AAC-focused therapist options near "
            f"{zip_code} and compare them against {insurance_note} for parent review."
        ),
    }


async def file_iep_request(child_profile: dict, school_district: str):
    name = child_profile.get("name", "your child")
    grade = child_profile.get("grade", "")
    disability = child_profile.get("disability_category") or "Autism Spectrum Disorder"

    if not os.getenv("TINYFISH_API_KEY"):
        return _iep_demo_payload(name, school_district, grade, disability)

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                "https://api.tinyfish.ai/v1/agent/run",
                headers={"Authorization": f"Bearer {os.getenv('TINYFISH_API_KEY')}"},
                json={
                    "task": (
                        f"Review {school_district}'s IEP request workflow and prepare a parent-review request packet "
                        f"for {name}. Do not submit forms, send messages, or complete filing steps without explicit "
                        "parent approval."
                    ),
                    "context": {
                        "child_name": name,
                        "child_age": child_profile.get("age"),
                        "grade": grade,
                        "disability_category": disability,
                        "requested_support": "IEP evaluation and AAC-related school supports",
                        "parent_control_notice": PARENT_REVIEW_NOTICE,
                    },
                    "return_when": "results_compiled",
                },
            )
        return _normalize_agent_response(
            response.json(),
            f"TinyFish prepared an IEP review packet for {name}.",
            IEP_AGENT_STEPS,
        )
    except (httpx.ConnectError, httpx.TimeoutException):
        return _iep_demo_payload(name, school_district, grade, disability)


async def appeal_insurance_denial(child_profile: dict, insurance_provider: str, denial_reason: str):
    name = child_profile.get("name", "your child")

    if not os.getenv("TINYFISH_API_KEY"):
        return _appeal_demo_payload(name, insurance_provider, denial_reason)

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                "https://api.tinyfish.ai/v1/agent/run",
                headers={"Authorization": f"Bearer {os.getenv('TINYFISH_API_KEY')}"},
                json={
                    "task": (
                        f"Review {insurance_provider}'s appeal workflow and prepare a parent-review AAC denial appeal "
                        f"packet for {name}. Do not submit forms, send messages, or finalize the appeal without "
                        "explicit parent approval."
                    ),
                    "context": {
                        **child_profile,
                        "insurance_provider": insurance_provider,
                        "denial_reason": denial_reason,
                        "parent_control_notice": PARENT_REVIEW_NOTICE,
                    },
                    "return_when": "results_compiled",
                },
            )
        return _normalize_agent_response(
            response.json(),
            f"TinyFish prepared an appeal review packet for {name}.",
            APPEAL_AGENT_STEPS,
        )
    except (httpx.ConnectError, httpx.TimeoutException):
        return _appeal_demo_payload(name, insurance_provider, denial_reason)


async def search_therapists(child_profile: dict, zip_code: str, insurance_provider: str = ""):
    name = child_profile.get("name", "your child")

    if not os.getenv("TINYFISH_API_KEY"):
        return _therapist_demo_payload(zip_code, insurance_provider)

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                "https://api.tinyfish.ai/v1/agent/run",
                headers={"Authorization": f"Bearer {os.getenv('TINYFISH_API_KEY')}"},
                json={
                    "task": (
                        f"Search for AAC-experienced speech-language pathologists near ZIP {zip_code} for {name}, "
                        "compile parent-review options, and do not contact anyone on the parent's behalf."
                    ),
                    "context": {
                        **child_profile,
                        "zip_code": zip_code,
                        "insurance_provider": insurance_provider,
                        "specialty_focus": "AAC",
                        "parent_control_notice": "Parent review is required before outreach.",
                    },
                    "return_when": "results_compiled",
                },
            )
        return _normalize_agent_response(
            response.json(),
            f"TinyFish prepared therapist options near {zip_code}.",
            THERAPIST_AGENT_STEPS,
        )
    except (httpx.ConnectError, httpx.TimeoutException):
        return _therapist_demo_payload(zip_code, insurance_provider)
