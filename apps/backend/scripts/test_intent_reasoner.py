"""
Standalone test for intent_reasoner — run before wiring up the full stack.
Usage: python scripts/test_intent_reasoner.py
    Requires: OPENROUTER_API_KEY in environment or .env file for live mode.
    Without a key, the intent reasoner returns deterministic demo results.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))

from app.ml.intent_reasoner import classify_intent


class MockChild:
    name = "Alex"
    age = 5.0
    behavior_profile = {
        "hunger_sounds": ["mmm", "ah"],
        "known_gestures": {"reach_forward": "wants food", "wave": "hello"},
    }


async def main():
    gesture = {"has_hand": True, "landmarks": [(0.5, 0.3, 0.1)] * 10}
    audio = {"transcript": "mmm", "confidence": 0.85}
    context = {"time_of_day": "afternoon", "recent_intents": []}

    result = await classify_intent(gesture, audio, MockChild(), context)
    print("Intent classification result:")
    for intent in result["intents"]:
        print(f"  {intent['label']}: {intent['confidence']:.0%} — {intent['explanation']}")


if __name__ == "__main__":
    asyncio.run(main())
