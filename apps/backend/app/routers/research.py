from fastapi import APIRouter
from pydantic import BaseModel
from app.core.llm_client import chat_model, client, llm_configured

router = APIRouter(prefix="/research", tags=["research"])

RESEARCH_SYSTEM = """You are a knowledgeable AAC advocate and resource specialist helping parents of non-verbal children navigate insurance, IEP processes, school systems, and therapy options.

Provide clear, actionable, step-by-step guidance. When discussing insurance appeals or IEP requests, include:
- Specific language to use
- Legal rights (IDEA, ADA where applicable)
- Typical timelines
- What to escalate if steps fail

Keep responses warm but practical. Parents are often overwhelmed — help them feel capable."""


class ResearchQuery(BaseModel):
    question: str
    child_age: float = None
    state: str = None


@router.post("/ask")
async def ask_research(payload: ResearchQuery):
    context = ""
    if payload.child_age:
        context += f"Child age: {payload.child_age}. "
    if payload.state:
        context += f"State: {payload.state}. "

    fallback = (
        "Demo guidance: document the communication need, request an AAC evaluation in writing, "
        "ask for assistive technology supports in the IEP meeting, and keep copies of every request. "
        "For insurance, ask the clinician for a letter of medical necessity and appeal with the denial reason addressed directly."
    )

    if not llm_configured():
        return {"answer": fallback}

    try:
        response = await client.chat.completions.create(
            model=chat_model(),
            max_tokens=800,
            messages=[
                {"role": "system", "content": RESEARCH_SYSTEM},
                {"role": "user", "content": f"{context}{payload.question}"},
            ],
        )
    except Exception:
        return {"answer": fallback}

    return {"answer": response.choices[0].message.content}
