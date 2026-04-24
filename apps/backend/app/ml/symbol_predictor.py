import json
from datetime import datetime
from app.core.llm_client import chat_model, client, llm_configured

SYMBOLS = [
    "Snack", "Water", "Bathroom", "Tired", "Play", "Hug", "Hurt", "Happy",
    "Sad", "Music", "Outside", "TV", "Stop", "More", "Help", "No", "Yes",
    "Break", "All Done", "Too Loud", "Different", "Pain",
    "Story", "Light Off", "Scared", "Teacher",
]

CONTEXT_SYMBOLS = {
    "mealtime": ["Water", "Snack", "More", "All Done", "Help", "Break"],
    "bedtime":  ["Tired", "Bathroom", "Story", "Light Off", "Scared", "Hug"],
    "school":   ["Help", "Break", "Teacher", "Too Loud", "All Done", "Bathroom"],
    "therapy":  ["More", "Stop", "Help", "Yes", "No", "Break"],
}

_CONTEXT_LABELS = {
    "mealtime": "Mealtime",
    "bedtime":  "Bedtime",
    "school":   "School",
    "therapy":  "Therapy",
}


def _fallback_symbols(context: dict, behavior_profile: dict, recent_intents: list) -> list:
    context_name = str((context or {}).get("name") or (context or {}).get("activity") or "").lower()
    context_display = _CONTEXT_LABELS.get(context_name, context_name.capitalize() if context_name else "Current")
    confirmed = behavior_profile.get("confirmed_intents", {}) if behavior_profile else {}

    seen = set()
    results = []

    # 1. Context-specific symbols
    for label in CONTEXT_SYMBOLS.get(context_name, []):
        if label not in seen:
            results.append({"label": label, "reason": f"{context_display} context"})
            seen.add(label)

    # 2. Most-confirmed intents
    for intent_label, count in sorted(confirmed.items(), key=lambda x: -x[1]):
        for symbol in SYMBOLS:
            if symbol.lower() in intent_label.lower() and symbol not in seen:
                count_str = f"{count} time{'s' if count != 1 else ''}"
                results.append({"label": symbol, "reason": f"Confirmed {count_str} this week"})
                seen.add(symbol)

    # 3. Recently selected symbols from intent logs
    for intent_group in recent_intents or []:
        for intent in intent_group or []:
            label_text = intent.get("label", "")
            for symbol in SYMBOLS:
                if symbol.lower() in label_text.lower() and symbol not in seen:
                    results.append({"label": symbol, "reason": "Recently selected"})
                    seen.add(symbol)

    if not results:
        fallback = ["Water", "Help", "Break", "More", "All Done", "No", "Yes", "Stop"]
        results = [{"label": l, "reason": "Common choice"} for l in fallback]

    return [
        {
            "label": r["label"],
            "score": round(max(0.3, 0.92 - i * 0.07), 2),
            "reason": r["reason"],
        }
        for i, r in enumerate(results[:8])
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
    context_display = _CONTEXT_LABELS.get(context_name, context_name.capitalize() if context_name else "Current")

    if not llm_configured():
        return _fallback_symbols(context or {}, behavior_profile, recent_intents)

    try:
        response = await client.chat.completions.create(
            model=chat_model(),
            max_tokens=300,
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
  {{"label": "Water", "score": 0.88, "reason": "{context_display} context"}},
  {{"label": "Help", "score": 0.74, "reason": "Confirmed 3 times this week"}},
  {{"label": "Break", "score": 0.65, "reason": "Recently selected"}}
]}}

The reason field must be one of:
- "{context_display} context" (for symbols that match the current activity)
- "Confirmed N times this week" (for symbols the child has confirmed before, where N is the count)
- "Recently selected" (for symbols appearing in recent intents)
- A brief one-phrase explanation if none of the above fit""",
                }
            ],
            response_format={"type": "json_object"},
        )
    except Exception:
        return _fallback_symbols(context or {}, behavior_profile, recent_intents)

    content = json.loads(response.choices[0].message.content)
    return _normalize_symbols(content)
