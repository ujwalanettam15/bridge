import json
from datetime import datetime
from app.core.llm_client import chat_model, client, llm_configured

SYMBOLS = [
    "Snack", "Water", "Bathroom", "Tired", "Play", "Hug", "Hurt", "Happy",
    "Sad", "Music", "Outside", "TV", "Stop", "More", "Help", "No", "Yes",
    "Break", "All Done", "Too Loud", "Different", "Pain",
]

CONTEXT_SYMBOLS = {
    "mealtime": ["Water", "Snack", "More", "All Done", "Help", "Break", "Different", "No"],
    "bedtime": ["Tired", "Bathroom", "Hug", "Help", "Stop", "Break", "Yes", "No"],
    "school": ["Help", "Break", "Too Loud", "Bathroom", "All Done", "Different", "Yes", "No"],
    "therapy": ["More", "Stop", "Help", "Yes", "No", "Break", "Pain", "All Done"],
}


def _fallback_symbols(context: dict, behavior_profile: dict, recent_intents: list) -> list:
    context_name = str((context or {}).get("name") or (context or {}).get("activity") or "").lower()
    labels = CONTEXT_SYMBOLS.get(context_name, [])
    confirmed = behavior_profile.get("confirmed_intents", {}) if behavior_profile else {}

    for intent_group in recent_intents or []:
        for intent in intent_group or []:
            label = intent.get("label", "")
            for symbol in SYMBOLS:
                if symbol.lower() in label.lower() and symbol not in labels:
                    labels.insert(0, symbol)

    for label in confirmed:
        for symbol in SYMBOLS:
            if symbol.lower() in label.lower() and symbol not in labels:
                labels.insert(0, symbol)

    labels = labels or ["Water", "Help", "Break", "More", "All Done", "No", "Yes", "Stop"]
    return [
        {
            "label": label,
            "score": round(max(0.3, 0.92 - i * 0.07), 2),
            "reason": "Suggested from current context and confirmed history.",
        }
        for i, label in enumerate(labels[:8])
    ]


def _normalize_symbols(content) -> list:
    if isinstance(content, dict):
        content = content.get("symbols", list(content.values())[0] if content else [])
    if not isinstance(content, list):
        return []
    normalized = []
    for i, item in enumerate(content[:8]):
        if isinstance(item, str):
            normalized.append(
                {
                    "label": item,
                    "score": round(max(0.3, 0.92 - i * 0.07), 2),
                    "reason": "Ranked by the Bridge symbol predictor.",
                }
            )
        elif isinstance(item, dict):
            normalized.append(
                {
                    "label": item.get("label", item.get("symbol", "Help")),
                    "score": float(item.get("score", item.get("confidence", 0.8))),
                    "reason": item.get("reason", "Ranked by the Bridge symbol predictor."),
                }
            )
    return normalized


async def predict_symbols(child_id: str, behavior_profile: dict, recent_intents: list, context: dict = None) -> list:
    hour = datetime.now().hour
    time_context = "morning" if hour < 12 else "afternoon" if hour < 18 else "evening"
    context_name = (context or {}).get("name") or (context or {}).get("activity") or "none"

    if not llm_configured():
        return _fallback_symbols(context or {}, behavior_profile, recent_intents)

    try:
        response = await client.chat.completions.create(
            model=chat_model(),
            max_tokens=200,
            messages=[
                {
                    "role": "user",
                    "content": f"""Given this child's behavioral profile and context, rank these AAC symbols by likelihood of use right now.

Available symbols: {SYMBOLS}
Current activity context: {context_name}
Time of day: {time_context}
Child's behavioral profile: {json.dumps(behavior_profile)}
Recent intents (last 30 min): {json.dumps(recent_intents)}

Return ONLY JSON in this shape:
{{"symbols": [
  {{"label": "Water", "score": 0.88, "reason": "Mealtime context and confirmed drink requests"}},
  {{"label": "Break", "score": 0.74, "reason": "Recent frustration cue"}}
]}}""",
                }
            ],
            response_format={"type": "json_object"},
        )
    except Exception:
        return _fallback_symbols(context or {}, behavior_profile, recent_intents)

    content = json.loads(response.choices[0].message.content)
    return _normalize_symbols(content)
