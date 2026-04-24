import json
from datetime import datetime
from app.core.llm_client import chat_model, client, llm_configured


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

    fallback = (
        f"{child_name} had {len(today_logs)} recorded communication moment(s) today. "
        f"The most common signals were: {', '.join(list(intent_summary.keys())[:3]) or 'emerging patterns'}. "
        "Reviewing these confirmations with a therapist can help refine tomorrow's board."
    )

    if not llm_configured():
        return fallback

    try:
        response = await client.chat.completions.create(
            model=chat_model(),
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
    except Exception:
        return fallback

    return response.choices[0].message.content
