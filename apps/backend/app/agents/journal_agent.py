import json
import re
from datetime import datetime, timedelta
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

Suggested intent frequency data (parent-confirmed communication signals): {json.dumps(intent_summary)}
Total session moments: {len(today_logs)}

Write as if summarizing their communicative day. Be warm, child-centered, and dignity-preserving — focus on their communication efforts and strengths. Do not use clinical or diagnostic language. Do not mention AI or technology.""",
                }
            ],
        )
    except Exception:
        return fallback

    return response.choices[0].message.content


async def generate_therapist_summary(child_id: str, child_name: str, db) -> dict:
    from app.models import IntentLog

    week_start = datetime.utcnow() - timedelta(days=7)
    logs = (
        db.query(IntentLog)
        .filter(
            IntentLog.child_id == child_id,
            IntentLog.timestamp >= week_start,
        )
        .order_by(IntentLog.timestamp.desc())
        .all()
    )

    total_attempts = len(logs)

    confirmed_counts: dict = {}
    for log in logs:
        if log.confirmed_label:
            confirmed_counts[log.confirmed_label] = confirmed_counts.get(log.confirmed_label, 0) + 1

    intent_counts: dict = {}
    for log in logs:
        if not log.ranked_intents:
            continue
        top = log.ranked_intents[0]
        label = top["label"]
        intent_counts[label] = intent_counts.get(label, 0) + 1

    repeated = [label for label, count in intent_counts.items() if count >= 3]
    observed = list(intent_counts.keys())[:10]
    confirmed_set = set(confirmed_counts.keys())
    suggested_add = [label for label in observed if label not in confirmed_set][:3]

    fallback = {
        "child_name": child_name,
        "period": "Last 7 days",
        "total_attempts": total_attempts,
        "observed_attempts": observed[:8] if observed else ["No communication attempts recorded in this period"],
        "confirmed_intents": [
            {"label": label, "count": count}
            for label, count in sorted(confirmed_counts.items(), key=lambda x: -x[1])
        ] if confirmed_counts else [{"label": "No confirmed intents yet", "count": 0}],
        "repeated_patterns": repeated if repeated else ["No repeated patterns identified yet — continue logging sessions"],
        "suggested_board_changes": suggested_add if suggested_add else ["Continue current symbol set — more session data needed"],
        "questions_for_session": [
            f"What strategies have been most effective for {child_name}'s communication this week?",
            "Are there specific times of day or contexts where communication attempts increase or drop off?",
            "Should any symbols be added, removed, or repositioned based on this week's usage patterns?",
            f"How is {child_name} responding to the current symbol board layout across different contexts?",
            "What communication goals should we prioritize for the next two weeks?",
        ],
        "generated_by": "demo_mode",
    }

    if not llm_configured() or total_attempts == 0:
        return fallback

    try:
        response = await client.chat.completions.create(
            model=chat_model(),
            max_tokens=900,
            messages=[
                {
                    "role": "user",
                    "content": f"""Generate a structured clinical therapist summary for {child_name}'s AAC communication over the last 7 days.

Session data:
- Total session moments logged: {total_attempts}
- Parent-confirmed intents (label → count): {json.dumps(confirmed_counts)}
- Top AI-suggested intents (label → frequency, for context only): {json.dumps(intent_counts)}
- Repeated patterns (3+ occurrences): {json.dumps(repeated)}

Return a JSON object with exactly these keys:
- "observed_attempts": list of 3-6 concise strings describing observed communication attempts, referencing actual data
- "confirmed_intents": list of objects with "label" (string) and "count" (integer)
- "repeated_patterns": list of 2-4 strings describing repeated communication patterns with clinical relevance
- "suggested_board_changes": list of 2-4 specific strings recommending symbol board modifications
- "questions_for_session": list of 4-5 strings with specific, data-grounded questions for the therapist

Be clinical, specific, and actionable. Reference the actual labels and counts from the data provided. Return only valid JSON with no markdown.""",
                }
            ],
        )
        raw = response.choices[0].message.content.strip()
        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group())
            result = {**fallback, **parsed}
            result["child_name"] = child_name
            result["period"] = "Last 7 days"
            result["total_attempts"] = total_attempts
            result["generated_by"] = "llm"
            if "confirmed_intents" not in parsed or not isinstance(parsed["confirmed_intents"], list):
                result["confirmed_intents"] = fallback["confirmed_intents"]
            return result
    except Exception:
        pass

    return fallback
