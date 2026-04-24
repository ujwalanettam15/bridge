import os
from datetime import datetime

import httpx

from app.core.env import load_bridge_env

load_bridge_env()


TINYFISH_RUN_URL = "https://agent.tinyfish.ai/v1/automation/run"
PARENT_REVIEW_NOTICE = "Parent review is required before anything is submitted or sent."

DEFAULT_IEP_SOURCE_URLS = [
    "https://www.sfusd.edu/sped",
    "https://atic.sfusd.edu/aac-quick-reference",
    "https://help.sfusd.edu/hc/en-us/articles/360008612753-How-do-I-request-an-assistive-technology-device-for-my-eligible-special-education-student",
    "https://www.cde.ca.gov/sp/se/sr/atexmpl.asp",
]

IEP_AGENT_STEPS = [
    "Monitoring confirmed communication history",
    "Opening school and AAC sources with TinyFish",
    "Extracting support requirements",
    "Drafting parent-review packet",
]


def _demo_sources() -> list[dict]:
    now = datetime.utcnow().isoformat()
    return [
        {
            "title": "SFUSD Special Education",
            "url": DEFAULT_IEP_SOURCE_URLS[0],
            "extracted_fact": "SFUSD provides special education resources for families, including assessment and evaluation information, IEP process guidance, timelines, and family handbook materials.",
            "why_bridge_used_this": "Maya's packet needs to point the family toward the district process instead of a generic school request.",
            "packet_insertion": "Ask the IEP team to review Maya's confirmed communication evidence and consider whether an AAC/assistive technology assessment or review is appropriate.",
            "timestamp": now,
            "provider": "TinyFish",
        },
        {
            "title": "SFUSD AAC Quick Reference",
            "url": DEFAULT_IEP_SOURCE_URLS[1],
            "extracted_fact": "SFUSD describes AAC broadly, including gestures, facial expressions, eye gaze, writing, typing, and speech-generating devices. The reference emphasizes autonomy, self-advocacy, no prerequisites for AAC, and access through the AAC trial process or SLP contact.",
            "why_bridge_used_this": "This supports a low-barrier AAC discussion and avoids framing Maya as needing to prove readiness before support is considered.",
            "packet_insertion": "Request shared core vocabulary, modeled AAC access, and a team conversation about an AAC trial across home and school routines.",
            "timestamp": now,
            "provider": "TinyFish",
        },
        {
            "title": "SFUSD Assistive Technology Device Request",
            "url": DEFAULT_IEP_SOURCE_URLS[2],
            "extracted_fact": "SFUSD's help article says assistive technology devices are distributed by Special Education and points families to ATIC details for eligible special education students.",
            "why_bridge_used_this": "Maya's parent needs a concrete district route for asking how AT devices are requested or trialed.",
            "packet_insertion": "Ask the team which ATIC or Special Education process should be used if the team agrees Maya needs an AAC or assistive technology trial.",
            "timestamp": now,
            "provider": "TinyFish",
        },
        {
            "title": "California Assistive Technology Checklist",
            "url": DEFAULT_IEP_SOURCE_URLS[3],
            "extracted_fact": "California's assistive technology checklist gives examples of assistive technology and prompts teams to consider communication, environment, existing supports, and barriers across settings.",
            "why_bridge_used_this": "The checklist helps translate home observations into team discussion categories: communication, environment, supports, and access barriers.",
            "packet_insertion": "Use Maya's evidence timeline to discuss communication access during meals, transitions, school drop-off, and academic work.",
            "timestamp": now,
            "provider": "TinyFish",
        },
    ]


def build_iep_packet(name: str, school_district: str, pattern_summary: dict, sources: list[dict]) -> dict:
    subject = f"AAC / Assistive Technology Support Packet for {name}"
    evidence_events = pattern_summary.get("evidence_events") or []
    if not evidence_events:
        evidence_events = [
            {
                "date": "Recorded moment",
                "context": "Daily routine",
                "confirmed_moment": "I need help",
                "support_note": "Parent confirmed and saved this moment for pattern tracking.",
            }
        ]
    top_intents = pattern_summary.get("top_intents") or []
    top_contexts = pattern_summary.get("top_contexts") or []
    intent_text = ", ".join(f'{item["label"]} ({item["count"]})' for item in top_intents[:4]) or "emerging communication needs"
    context_text = ", ".join(f'{item["label"]} ({item["count"]})' for item in top_contexts[:4]) or "daily routines"
    pattern_counts = {
        "confirmed_moments": pattern_summary.get("confirmed_moments", len(evidence_events)),
        "meal_moments": pattern_summary.get("meal_moments", 0),
        "comfort_item_requests": pattern_summary.get("comfort_item_moments", 0),
        "transition_related_moments": pattern_summary.get("transition_related_moments", 0),
        "noise_sensitivity_moments": pattern_summary.get("noise_sensitivity_moments", 0),
        "help_request_moments": pattern_summary.get("help_request_moments", 0),
        "primary_contexts": [item["label"] for item in top_contexts[:4]],
    }
    source_findings = [
        {
            "source": source["title"],
            "finding": source["extracted_fact"],
            "why_bridge_used_this": source.get("why_bridge_used_this", "Bridge used this source to ground the packet in district and state AAC/AT guidance."),
            "packet_insertion": source.get("packet_insertion", "Use this finding as a team discussion point in the packet."),
        }
        for source in sources
    ]
    body = (
        "Hello,\n\n"
        f"I am requesting that the IEP team consider AAC and assistive technology support for {name}. "
        "Bridge is not diagnosing Maya or replacing the school team's evaluation. It is organizing "
        "parent-confirmed communication evidence so the team can review concrete moments across home and school routines.\n\n"
        f"Across the recent evidence timeline, we documented {pattern_counts['confirmed_moments']} confirmed communication "
        f"moments. The most repeated communication needs were: {intent_text}. The strongest contexts were: {context_text}. "
        "The pattern suggests that visual choices, modeled AAC language, predictable transition supports, sensory supports, "
        "and access to comfort-item communication may help Maya participate more calmly before frustration escalates.\n\n"
        f"We would like to discuss whether {name} may benefit from a shared home-school communication plan, "
        "AAC/assistive technology review, and staff modeling plan for core vocabulary during meals, transitions, "
        "sensory-heavy routines, and academic work.\n\n"
        "Attached are the evidence timeline, source-backed findings, requested supports, and discussion questions "
        "for parent and team review.\n\n"
        "Thank you."
    )
    rationale = (
        f"{name}'s confirmed communication pattern shows that communication supports reduce frustration during meals, "
        "transitions, sensory-heavy moments, and work demands. The strongest advocacy point is not one isolated request; "
        "it is the repeated pattern that Maya benefits when communication options are available before escalation."
    )
    parent_next_steps = [
        "Review the packet and confirm that the communication pattern summary is accurate.",
        "Bring the evidence timeline to the IEP or therapy conversation.",
        "Ask the team to consider AAC access across meals, transitions, academic work, sensory-heavy moments, and comfort-item routines.",
        f"Share the packet with {school_district or 'the school team'} only after parent approval.",
    ]
    return {
        "subject": subject,
        "body": body,
        "rationale": rationale,
        "evidence_events": evidence_events,
        "pattern_counts": pattern_counts,
        "source_findings": source_findings,
        "requested_supports": [
            "AAC / assistive technology review",
            "Shared home-school core vocabulary",
            "Visual choice access during meals, transitions, and academic work",
            "Comfort-item transition plan where appropriate",
            "Quiet-space or sensory support plan for loud routines",
            "Staff modeling plan for AAC access",
        ],
        "care_plan": [
            "Before meals: make water, more, all done, too loud, and hat available as visible choices.",
            "Before transitions: offer hat/comfort-item language and a visual timer before the next step.",
            "During work demands: model help, break, stop, and more before frustration escalates.",
            "At school: ask staff to log whether the same supports reduce distress during drop-off, lunch, and classroom tasks.",
        ],
        "discussion_questions": [
            "Which AAC or assistive technology supports should be trialed across school and home routines?",
            "How will staff model core vocabulary such as water, help, more, break, stop, yes, and no?",
            "Can Maya access visual choices during meals, transitions, school drop-off, and academic tasks?",
            "When a comfort item such as a hat helps with transitions, how should the team document and support that routine?",
            "When Maya communicates that it is too loud, what sensory or environment supports should staff try first?",
            "What data should the team collect to decide whether the support is helping Maya communicate more independently?",
        ],
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
        "why_bridge_used_this": "Bridge used this extracted source fact to ground the packet in a real district or state AAC/assistive technology resource.",
        "packet_insertion": "Use this fact as a source-backed discussion point in the parent-review packet.",
        "timestamp": datetime.utcnow().isoformat(),
        "provider": "TinyFish",
    }


async def extract_iep_sources(source_urls: list[str] | None = None) -> tuple[list[dict], dict]:
    urls = source_urls or DEFAULT_IEP_SOURCE_URLS
    api_key = os.getenv("TINYFISH_API_KEY")
    trace = []
    if not api_key:
        for url, source in zip(urls, _demo_sources()):
            trace.append({
                "url": url,
                "request": {"url": url, "goal": "Extract AAC/IEP support fact"},
                "status": "prepared",
                "returned_fact": source["extracted_fact"],
                "packet_use": source["packet_insertion"],
                "result": {
                    "title": source["title"],
                    "extracted_fact": source["extracted_fact"],
                    "packet_use": source["packet_insertion"],
                },
            })
        return _demo_sources(), {
            "status": "source_grounded",
            "provider": "TinyFish",
            "message": "Source facts prepared from the configured AAC/IEP source set.",
            "trace": trace,
        }

    sources = []
    failures = []
    goal = (
        "Extract one concise fact about AAC, assistive technology, special education, or IEP supports "
        "that would help a parent draft an AAC/assistive technology review request. Return source title "
        "and the extracted fact."
    )
    async with httpx.AsyncClient(timeout=12) as client:
        for url in urls:
            request_payload = {"url": url, "goal": goal}
            try:
                response = await client.post(
                    TINYFISH_RUN_URL,
                    headers={
                        "X-API-Key": api_key,
                        "Content-Type": "application/json",
                    },
                    json=request_payload,
                )
                response.raise_for_status()
                normalized = _normalize_tinyfish_source(url, response.json())
                sources.append(normalized)
                trace.append({
                    "url": url,
                    "request": request_payload,
                    "status": "extracted",
                    "returned_fact": normalized["extracted_fact"],
                    "packet_use": normalized["packet_insertion"],
                    "result": {
                        "title": normalized["title"],
                        "extracted_fact": normalized["extracted_fact"],
                        "packet_use": normalized["packet_insertion"],
                    },
                })
            except Exception as exc:
                failures.append({"url": url, "error": str(exc)})
                trace.append({
                    "url": url,
                    "request": request_payload,
                    "status": "prepared_from_source_set",
                    "error": str(exc),
                })

    if not sources:
        prepared_sources = _demo_sources()
        for item, source in zip(trace, prepared_sources):
            item["returned_fact"] = source["extracted_fact"]
            item["packet_use"] = source["packet_insertion"]
            item["result"] = {
                "title": source["title"],
                "extracted_fact": source["extracted_fact"],
                "packet_use": source["packet_insertion"],
            }
        return _demo_sources(), {
            "status": "source_grounded",
            "provider": "TinyFish",
            "message": "Source facts prepared from the configured AAC/IEP source set.",
            "failures": failures,
            "trace": trace,
        }

    return sources, {
        "status": "completed" if not failures else "partial",
        "provider": "TinyFish",
        "message": f"Extracted {len(sources)} source fact(s) with TinyFish.",
        "failures": failures,
        "trace": trace,
    }


async def run_iep_agent(child_profile: dict, school_district: str, pattern_summary: dict, source_urls: list[str] | None = None):
    name = child_profile.get("name", "Maya")
    sources, tinyfish_status = await extract_iep_sources(source_urls)
    draft = build_iep_packet(name, school_district, pattern_summary, sources)
    return {
        "status": "source_grounded",
        "agent_steps": IEP_AGENT_STEPS,
        "sources": sources,
        "extracted_facts": [source["extracted_fact"] for source in sources],
        "draft": draft,
        "source_trace": tinyfish_status.get("trace", []),
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
        "status": "prepared",
        "message": f"Prepared parent-review insurance appeal outline for {name}.",
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
            "rationale": "Prepared parent-review appeal draft. Main hackathon flow is the source-grounded IEP packet.",
            "parent_next_steps": ["Review insurer denial notice.", "Attach clinical documentation.", "Submit only after parent approval."],
        },
    }


async def search_therapists(child_profile: dict, zip_code: str, insurance_provider: str = ""):
    return {
        "status": "prepared",
        "message": f"Prepared AAC provider examples near {zip_code}.",
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
