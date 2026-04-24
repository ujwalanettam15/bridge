"""
Test MediaPipe gesture extraction with a synthetic 100x100 black frame.
Usage: python scripts/test_mediapipe.py
No API keys required.
"""
import asyncio
import sys
import os
import base64
import numpy as np
import cv2

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.ml.mediapipe_processor import extract_gesture_vector


async def main():
    # Create a small test frame (black 100x100 image)
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    _, buf = cv2.imencode(".jpg", frame)
    frame_b64 = base64.b64encode(buf).decode()

    result = await extract_gesture_vector(frame_b64)
    print("MediaPipe result:")
    print(f"  has_hand: {result['has_hand']}")
    print(f"  landmark count: {len(result['landmarks'])}")
    print("  (no landmarks expected for blank frame — pipeline is working)")


if __name__ == "__main__":
    asyncio.run(main())
