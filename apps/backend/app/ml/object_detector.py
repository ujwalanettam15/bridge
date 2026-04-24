import base64


def _box(x: int, y: int, w: int, h: int, frame_w: int, frame_h: int) -> dict:
    return {
        "x": round(x / frame_w, 4),
        "y": round(y / frame_h, 4),
        "w": round(w / frame_w, 4),
        "h": round(h / frame_h, 4),
    }


def _best_contour_detection(mask, label: str, frame_w: int, frame_h: int, *, color: str):
    import cv2

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best = None
    frame_area = frame_w * frame_h

    for contour in contours:
        area = cv2.contourArea(contour)
        if area < frame_area * 0.003:
            continue
        x, y, w, h = cv2.boundingRect(contour)
        if w <= 0 or h <= 0:
            continue

        aspect = h / max(w, 1)
        width_ratio = w / frame_w
        height_ratio = h / frame_h

        if label == "water bottle":
            # Best demo prop: gray/silver bottle held upright in frame.
            if aspect < 1.25 or aspect > 8:
                continue
            if width_ratio > 0.34 or height_ratio > 0.88 or height_ratio < 0.12:
                continue
            confidence = min(0.94, 0.58 + area / (frame_area * 0.12) + min(aspect, 3.0) * 0.06)
        else:
            # Best demo prop: black/dark hat with a broad visible brim in the top/mid frame.
            if y > frame_h * 0.72:
                continue
            if not (width_ratio >= 0.08 and w >= h * 1.05):
                continue
            confidence = min(0.9, 0.55 + area / (frame_area * 0.16) + min(width_ratio, 0.45) * 0.28)

        candidate = {
            "label": label,
            "confidence": round(float(confidence), 2),
            "box": _box(x, y, w, h, frame_w, frame_h),
            "source": "opencv_color_shape",
            "cue": color,
        }
        if best is None or candidate["confidence"] > best["confidence"]:
            best = candidate

    return best


def _best_edge_bottle_detection(frame, frame_w: int, frame_h: int):
    import cv2

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    equalized = cv2.equalizeHist(gray)
    edges = cv2.Canny(equalized, 45, 120)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 9))
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    frame_area = frame_w * frame_h
    best = None

    for contour in contours:
        area = cv2.contourArea(contour)
        if area < frame_area * 0.004:
            continue

        x, y, w, h = cv2.boundingRect(contour)
        if w <= 0 or h <= 0:
            continue

        aspect = h / max(w, 1)
        width_ratio = w / frame_w
        height_ratio = h / frame_h
        x_center = (x + w / 2) / frame_w

        if not (1.6 <= aspect <= 7.5):
            continue
        if not (0.035 <= width_ratio <= 0.28 and 0.16 <= height_ratio <= 0.82):
            continue
        if y < frame_h * 0.04 or y > frame_h * 0.86:
            continue

        rect_area = w * h
        fill_ratio = area / max(rect_area, 1)
        if fill_ratio < 0.12:
            continue

        center_bonus = max(0, 0.12 - abs(x_center - 0.5) * 0.18)
        confidence = min(0.88, 0.5 + min(aspect, 4.2) * 0.055 + min(height_ratio, 0.55) * 0.35 + center_bonus)
        candidate = {
            "label": "water bottle",
            "confidence": round(float(confidence), 2),
            "box": _box(x, y, w, h, frame_w, frame_h),
            "source": "opencv_edge_shape",
            "cue": "upright bottle silhouette",
        }
        if best is None or candidate["confidence"] > best["confidence"]:
            best = candidate

    return best


async def detect_objects(frame_b64: str) -> list[dict]:
    try:
        import cv2
        import numpy as np
    except ImportError:
        return []

    try:
        if "," in frame_b64 and frame_b64.strip().lower().startswith("data:image"):
            frame_b64 = frame_b64.split(",", 1)[1]
        img_bytes = base64.b64decode(frame_b64)
        img_array = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    except Exception:
        return []

    if frame is None:
        return []

    frame_h, frame_w = frame.shape[:2]
    blurred = cv2.GaussianBlur(frame, (5, 5), 0)
    hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

    blue_mask = cv2.inRange(hsv, (88, 45, 35), (135, 255, 255))
    gray_mask = cv2.inRange(hsv, (0, 0, 35), (180, 75, 235))

    red_mask_a = cv2.inRange(hsv, (0, 60, 45), (12, 255, 255))
    red_mask_b = cv2.inRange(hsv, (168, 60, 45), (180, 255, 255))
    red_mask = cv2.bitwise_or(red_mask_a, red_mask_b)

    # Dark hats are common, but this fallback is intentionally conservative to avoid
    # turning every shadow into a hat.
    dark_mask = cv2.inRange(hsv, (0, 0, 0), (180, 95, 70))
    top_gate = np.zeros_like(dark_mask)
    top_gate[: int(frame_h * 0.72), :] = 255
    dark_mask = cv2.bitwise_and(dark_mask, top_gate)

    kernel = np.ones((5, 5), np.uint8)
    blue_mask = cv2.morphologyEx(blue_mask, cv2.MORPH_OPEN, kernel)
    blue_mask = cv2.morphologyEx(blue_mask, cv2.MORPH_CLOSE, kernel)
    gray_mask = cv2.morphologyEx(gray_mask, cv2.MORPH_OPEN, kernel)
    gray_mask = cv2.morphologyEx(gray_mask, cv2.MORPH_CLOSE, kernel)
    red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_OPEN, kernel)
    red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_CLOSE, kernel)
    dark_mask = cv2.morphologyEx(dark_mask, cv2.MORPH_OPEN, kernel)
    dark_mask = cv2.morphologyEx(dark_mask, cv2.MORPH_CLOSE, kernel)

    detections = []

    blue_water = _best_contour_detection(blue_mask, "water bottle", frame_w, frame_h, color="blue vertical prop")
    gray_water = _best_contour_detection(gray_mask, "water bottle", frame_w, frame_h, color="gray vertical prop")
    edge_water = _best_edge_bottle_detection(frame, frame_w, frame_h)
    water_candidates = [d for d in [gray_water, blue_water, edge_water] if d]
    if water_candidates:
        detections.append(max(water_candidates, key=lambda item: item["confidence"]))

    red_hat = _best_contour_detection(red_mask, "hat", frame_w, frame_h, color="red broad prop")
    dark_hat = _best_contour_detection(dark_mask, "hat", frame_w, frame_h, color="dark broad prop")
    hat_candidates = [d for d in [red_hat, dark_hat] if d]
    if hat_candidates:
        detections.append(max(hat_candidates, key=lambda item: item["confidence"]))

    return sorted(detections, key=lambda item: item["confidence"], reverse=True)
