import cv2
import numpy as np

# ─── HSV диапазоны ────────────────────────────────────────────────────────────
# Красный в HSV разорван на два диапазона (0-10 и 160-180)
RED_LOWER_1  = np.array([0,   100, 100])
RED_UPPER_1  = np.array([10,  255, 255])
RED_LOWER_2  = np.array([155, 100, 100])
RED_UPPER_2  = np.array([180, 255, 255])

GREEN_LOWER  = np.array([35,  60,  60])
GREEN_UPPER  = np.array([95,  255, 255])

YELLOW_LOWER = np.array([15,  80,  80])
YELLOW_UPPER = np.array([38,  255, 255])

# Минимальный % пикселей нужного цвета чтобы принять решение
MIN_COLOR_RATIO = 0.03   # 3%

# ── DEBUG режим ───────────────────────────────────────────────────────────────
# Поставь True → в консоли будут печататься реальные H,S,V значения светофора.
# Посмотри какой H (Hue) у горящей лампочки и скажи — подправим диапазоны.
# Поставь False когда всё заработает правильно.
DEBUG = True
# ─────────────────────────────────────────────────────────────────────────────


def detect_traffic_light_color(frame, box: tuple) -> str | None:
    """
    Анализирует центральную часть bounding box светофора по HSV.
    Возвращает: 'red', 'green', 'yellow' или None.
    """
    x1, y1, x2, y2 = box
    h = y2 - y1
    w = x2 - x1

    if h <= 0 or w <= 0:
        return None

    # Берём центральные 60% по высоте и ширине — убираем края/фон
    margin_y = int(h * 0.15)
    margin_x = int(w * 0.15)
    roi = frame[
        y1 + margin_y : y2 - margin_y,
        x1 + margin_x : x2 - margin_x
    ]

    if roi.size == 0:
        return None

    hsv   = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    total = roi.shape[0] * roi.shape[1]
    if total == 0:
        return None

    # Маски
    red_mask = (
        cv2.inRange(hsv, RED_LOWER_1, RED_UPPER_1) |
        cv2.inRange(hsv, RED_LOWER_2, RED_UPPER_2)
    )
    green_mask  = cv2.inRange(hsv, GREEN_LOWER,  GREEN_UPPER)
    yellow_mask = cv2.inRange(hsv, YELLOW_LOWER, YELLOW_UPPER)

    red_ratio    = np.count_nonzero(red_mask)    / total
    green_ratio  = np.count_nonzero(green_mask)  / total
    yellow_ratio = np.count_nonzero(yellow_mask) / total

    if DEBUG:
        # Средний HSV пикселя в ROI — смотри H чтобы понять реальный цвет
        mean_hsv = cv2.mean(hsv)[:3]
        # Самый яркий пиксель (V канал) — где горит лампочка
        bright_mask = hsv[:, :, 2] > 150
        if np.any(bright_mask):
            bright_h = hsv[:, :, 0][bright_mask]
            bright_s = hsv[:, :, 1][bright_mask]
            median_h = int(np.median(bright_h))
            median_s = int(np.median(bright_s))
        else:
            median_h = int(mean_hsv[0])
            median_s = int(mean_hsv[1])

        print(
            f"[TL DEBUG] "
            f"mean H={mean_hsv[0]:.0f} S={mean_hsv[1]:.0f} V={mean_hsv[2]:.0f} | "
            f"bright pixels → H={median_h} S={median_s} | "
            f"red={red_ratio:.2%}  green={green_ratio:.2%}  yellow={yellow_ratio:.2%}"
        )

    scores = {
        "red":    red_ratio,
        "green":  green_ratio,
        "yellow": yellow_ratio,
    }

    best_color, best_score = max(scores.items(), key=lambda x: x[1])

    if best_score < MIN_COLOR_RATIO:
        return None

    return best_color