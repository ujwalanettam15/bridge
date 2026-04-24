import openai
import json
from datetime import datetime

client = openai.AsyncOpenAI()

SYMBOLS = [
    "Snack", "Water", "Bathroom", "Tired", "Play", "Hug", "Hurt", "Happy",
    "Sad", "Music", "Outside", "TV", "Stop", "More", "Help", "No", "Yes",
]


async def predict_symbols(child_id: str, behavior_profile: dict, recent_intents: list) -> list:
    hour = datetime.now().hour
    time_context = "morning" if hour < 12 else "afternoon" if hour < 18 else "evening"

    response = await client.chat.completions.create(
        model="gpt-4o",
        max_tokens=200,
        messages=[
            {
                "role": "user",
                "content": f"""Given this child's behavioral profile and context, rank these AAC symbols by likelihood of use right now.

Available symbols: {SYMBOLS}
Time of day: {time_context}
Child's behavioral profile: {json.dumps(behavior_profile)}
Recent intents (last 30 min): {json.dumps(recent_intents)}

Return ONLY a JSON array of the top 8 symbol names in order of likelihood.
Example: ["Snack", "Water", "Play", "Happy", "More", "TV", "Tired", "Hug"]""",
            }
        ],
        response_format={"type": "json_object"},
    )

    content = json.loads(response.choices[0].message.content)
    # model returns {"symbols": [...]} or just an array — handle both
    return content if isinstance(content, list) else content.get("symbols", list(content.values())[0])
