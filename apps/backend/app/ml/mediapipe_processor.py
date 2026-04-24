import base64


async def extract_gesture_vector(frame_b64: str) -> dict:
    try:
        import cv2
        import mediapipe as mp
        import numpy as np
    except ImportError:
        return {
            "landmarks": [],
            "has_hand": False,
            "demo_mode": True,
            "note": "MediaPipe/OpenCV dependencies are not installed in this environment.",
        }

    img_bytes = base64.b64decode(frame_b64)
    img_array = np.frombuffer(img_bytes, np.uint8)
    frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

    if frame is None:
        return {"landmarks": [], "has_hand": False}

    mp_holistic = mp.solutions.holistic
    with mp_holistic.Holistic(static_image_mode=True) as holistic:
        results = holistic.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

    landmarks = []
    if results.pose_landmarks:
        landmarks = [(lm.x, lm.y, lm.z) for lm in results.pose_landmarks.landmark]
    if results.right_hand_landmarks:
        landmarks += [(lm.x, lm.y, lm.z) for lm in results.right_hand_landmarks.landmark]
    if results.left_hand_landmarks:
        landmarks += [(lm.x, lm.y, lm.z) for lm in results.left_hand_landmarks.landmark]

    has_hand = (
        results.right_hand_landmarks is not None
        or results.left_hand_landmarks is not None
    )

    return {"landmarks": landmarks, "has_hand": has_hand}
