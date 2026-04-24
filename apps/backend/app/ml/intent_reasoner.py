import json
from app.models import Child
from app.core.llm_client import chat_model, client, llm_configured

SYSTEM_PROMPT = """You are an AAC (Augmentative and Alternative Communication) assistant helping parents of non-verbal and minimally verbal autistic children understand their child's intent.

You will receive:
- Gesture/pose landmark data from a camera
- Audio transcription of any sounds/vocalizations
- The child's behavioral history and known patterns
- Context (time of day, recent intents)

Return ONLY valid JSON in this exact format:
{
  "intents": [
    {"label": "Wants snack", "confidence": 0.73, "explanation": "Reaching gesture toward kitchen area, vocalization matches known hunger sound"},
    {"label": "Tired", "confidence": 0.18, "explanation": "Eye rubbing gesture detected"},
    {"label": "Wants toy", "confidence": 0.09, "explanation": "Pointing gesture, afternoon context"}
  ]
}

Rules:
- Always return 2-4 intents ranked by confidence, summing to ~1.0
- Use the child's specific behavioral profile to personalize
- Explanations should be parent-friendly, not technical
- Labels should be natural phrases a parent would say"""


def _demo_intents(context: dict, gesture: dict, child: Child) -> dict:
    context_name = (context or {}).get("name") or (context or {}).get("activity") or "mealtime"
    profile = child.behavior_profile or {}
    confirmed = profile.get("confirmed_intents", {})

    presets = {
        "mealtime": [
            ("I want water", 0.72, "Mealtime context plus a reaching pattern that often matches drink requests."),
            ("I need a break", 0.18, "Body posture suggests possible frustration or fatigue."),
            ("I want more", 0.10, "Recent mealtime choices make another serving possible."),
        ],
        "bedtime": [
            ("I am tired", 0.68, "Bedtime context and slower movement make tired the most likely choice."),
            ("I need the bathroom", 0.20, "This is a common bedtime request for this profile."),
            ("I want a hug", 0.12, "The gesture could also be a comfort-seeking cue."),
        ],
        "school": [
            ("I need help", 0.64, "School context and hand movement suggest a request for support."),
            ("It is too loud", 0.22, "The profile shows confirmed break requests during noisy moments."),
            ("I need a break", 0.14, "Reduced engagement can indicate a break request."),
        ],
        "therapy": [
            ("I want more", 0.58, "Therapy context and forward reach may indicate wanting to continue."),
            ("Stop please", 0.25, "The movement could also signal refusal or discomfort."),
            ("I need help", 0.17, "This pattern sometimes appears when a task is difficult."),
        ],
    }
    rows = presets.get(str(context_name).lower(), presets["mealtime"])

    intents = []
    for label, confidence, explanation in rows:
        if confirmed.get(label):
            confidence = min(confidence + 0.05, 0.9)
            explanation += f" This has been confirmed {confirmed[label]} time(s) before."
        intents.append({"label": label, "confidence": confidence, "explanation": explanation})

    total = sum(i["confidence"] for i in intents) or 1
    for intent in intents:
        intent["confidence"] = round(intent["confidence"] / total, 2)
    return {"intents": intents, "demo_mode": True}


def normalize_intents(result: dict) -> dict:
    intents = result.get("intents", [])
    normalized = []
    for item in intents:
        confidence = item.get("confidence", item.get("probability", 0))
        normalized.append(
            {
                "label": item.get("label", "Unknown intent"),
                "confidence": float(confidence or 0),
                "explanation": item.get("explanation", ""),
            }
        )
    return {**result, "intents": normalized}


async def classify_intent(gesture: dict, audio: dict, child: Child, context: dict) -> dict:
    if not llm_configured():
        return _demo_intents(context, gesture, child)

    user_message = f"""
Child profile: {json.dumps(child.behavior_profile)}
Child name: {child.name}, Age: {child.age}
Time of day: {context.get('time_of_day', 'unknown')}
Recent intents (last 5 min): {json.dumps(context.get('recent_intents', []))}

Gesture data:
- Hand detected: {gesture.get('has_hand', False)}
- Key landmarks: {json.dumps(gesture.get('landmarks', [])[:20])}

Audio:
- Transcript: "{audio.get('transcript', '')}"
- Confidence: {audio.get('confidence', 0)}

What is this child most likely communicating?"""

    try:
        response = await client.chat.completions.create(
            model=chat_model(),
            max_tokens=500,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            response_format={"type": "json_object"},
        )
    except Exception:
        return _demo_intents(context, gesture, child)

    return normalize_intents(json.loads(response.choices[0].message.content))
