import openai
import json
from datetime import datetime

client = openai.AsyncOpenAI()


async def generate_daily_journal(child_id: str, child_name: str, db) -> str:
    from app.models import IntentLog

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_logs = (
        db.query(IntentLog)
        .filter(
            IntentLog.child_id == child_id,
            IntentLog.timestamp >= today_start,
        )
        .all()
    )

    if not today_logs:
        return f"{child_name} had a quiet day with no recorded communication sessions."

    intent_summary: dict = {}
    for log in today_logs:
        if not log.ranked_intents:
            continue
        for intent in log.ranked_intents:
            label = intent["label"]
            intent_summary[label] = intent_summary.get(label, 0) + 1

    response = await client.chat.completions.create(
        model="gpt-4o",
        max_tokens=300,
        messages=[
            {
                "role": "user",
                "content": f"""Write a warm, 2-3 sentence daily journal entry for parents about their child {child_name}'s communication today.

Intent frequency data (what they tried to communicate): {json.dumps(intent_summary)}
Total interactions: {len(today_logs)}

Write as if summarizing their emotional and communicative day. Be warm and specific. Do not mention technical terms.""",
            }
        ],
    )

    return response.choices[0].message.content
