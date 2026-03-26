import cv2
import numpy as np

# ─── HSV диапазоны ────────────────────────────────────────────────────────────
# Красный разорван на два диапазона (0-10 и 155-180)
RED_LOWER_1  = np.array([0,   100, 100])
RED_UPPER_1  = np.array([10,  255, 255])
RED_LOWER_2  = np.array([155, 100, 100])
RED_UPPER_2  = np.array([180, 255, 255])

GREEN_LOWER  = np.array([35,  60,  60])
GREEN_UPPER  = np.array([95,  255, 255])

YELLOW_LOWER = np.array([15,  80,  80])
YELLOW_UPPER = np.array([38,  255, 255])

MIN_COLOR_RATIO = 0.03   # минимум 3% пикселей нужного цвета


def detect_color(frame, box: tuple) -> str | None:
    """
    Анализирует центральную часть bounding box светофора.
    Возвращает: 'red', 'green', 'yellow' или None.
    """
    x1, y1, x2, y2 = box
    h = y2 - y1
    w = x2 - x1
    if h <= 0 or w <= 0:
        return None

    # Центральные 70% — убираем края/фон
    my = int(h * 0.15)
    mx = int(w * 0.15)
    roi = frame[y1 + my: y2 - my, x1 + mx: x2 - mx]

    if roi.size == 0:
        return None

    hsv   = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    total = roi.shape[0] * roi.shape[1]
    if total == 0:
        return None

    red_mask = (
        cv2.inRange(hsv, RED_LOWER_1, RED_UPPER_1) |
        cv2.inRange(hsv, RED_LOWER_2, RED_UPPER_2)
    )
    green_mask  = cv2.inRange(hsv, GREEN_LOWER,  GREEN_UPPER)
    yellow_mask = cv2.inRange(hsv, YELLOW_LOWER, YELLOW_UPPER)

    scores = {
        "red":    np.count_nonzero(red_mask)    / total,
        "green":  np.count_nonzero(green_mask)  / total,
        "yellow": np.count_nonzero(yellow_mask) / total,
    }

    best_color, best_score = max(scores.items(), key=lambda x: x[1])
    return best_color if best_score >= MIN_COLOR_RATIO else None