from fastapi import APIRouter
from pydantic import BaseModel
import openai

router = APIRouter(prefix="/research", tags=["research"])

client = openai.AsyncOpenAI()

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

    response = await client.chat.completions.create(
        model="gpt-4o",
        max_tokens=800,
        messages=[
            {"role": "system", "content": RESEARCH_SYSTEM},
            {"role": "user", "content": f"{context}{payload.question}"},
        ],
    )

    return {"answer": response.choices[0].message.content}
