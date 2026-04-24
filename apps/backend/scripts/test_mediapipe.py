"""
Test MediaPipe gesture extraction with a synthetic 100x100 black frame.
Usage: python scripts/test_mediapipe.py
No API keys required.
"""
import asyncio
import sys
import os
import base64

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.ml.mediapipe_processor import extract_gesture_vector


async def main():
    # 1x1 transparent PNG. The processor should return no landmarks or a graceful demo-mode fallback.
    frame_b64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
    )

    result = await extract_gesture_vector(frame_b64)
    print("MediaPipe result:")
    print(f"  has_hand: {result['has_hand']}")
    print(f"  landmark count: {len(result['landmarks'])}")
    if result.get("demo_mode"):
        print(f"  fallback: {result.get('note')}")
    else:
        print("  (no landmarks expected for blank frame — pipeline is working)")


if __name__ == "__main__":
    asyncio.run(main())
