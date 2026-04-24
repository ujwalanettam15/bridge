import openai
import json
from app.models import Child

client = openai.AsyncOpenAI()

SYSTEM_PROMPT = """You are an AAC (Augmentative and Alternative Communication) assistant helping parents of non-verbal and minimally verbal autistic children understand their child's intent.

You will receive:
- Gesture/pose landmark data from a camera
- Audio transcription of any sounds/vocalizations
- The child's behavioral history and known patterns
- Context (time of day, recent intents)

Return ONLY valid JSON in this exact format:
{
  "intents": [
    {"label": "Wants snack", "probability": 0.73, "explanation": "Reaching gesture toward kitchen area, vocalization matches known hunger sound"},
    {"label": "Tired", "probability": 0.18, "explanation": "Eye rubbing gesture detected"},
    {"label": "Wants toy", "probability": 0.09, "explanation": "Pointing gesture, afternoon context"}
  ]
}

Rules:
- Always return 2-4 intents ranked by probability, summing to ~1.0
- Use the child's specific behavioral profile to personalize
- Explanations should be parent-friendly, not technical
- Labels should be natural phrases a parent would say"""


async def classify_intent(gesture: dict, audio: dict, child: Child, context: dict) -> dict:
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

    response = await client.chat.completions.create(
        model="gpt-4o",
        max_tokens=500,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        response_format={"type": "json_object"},
    )

    return json.loads(response.choices[0].message.content)
