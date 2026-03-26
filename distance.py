# Реальные ширины объектов в метрах
REAL_WIDTH_M = {
    "person":        0.45,   # ширина плеч взрослого
    "car":           1.8,
    "traffic light": 0.25,
    "stop sign":     0.6,
    "bus":           2.5,
    "train":         3.0,
    "motorcycle":    0.7,
    "bicycle":       0.5,
}

# USB-камера 640px: человек на 2м занимает ~160-180px
# FOCAL_LENGTH = (pixel_w * known_dist) / real_width
# FOCAL_LENGTH = (170 * 2.0) / 0.45 ≈ 756
#
# Если всё ещё неточно — запусти calibrate.py и нажми C стоя на 2м
FOCAL_LENGTH = 756

def estimate_distance(label: str, box: tuple) -> float | None:
    """
    Возвращает расстояние в метрах.
    1.0 = 1 метр, 2.0 = 2 метра и т.д.
    """
    x1, y1, x2, y2 = box
    pixel_w = x2 - x1
    if pixel_w <= 0:
        return None
    real_w = REAL_WIDTH_M.get(label)
    if real_w is None:
        return None
    dist = (real_w * FOCAL_LENGTH) / pixel_w
    return round(dist, 2)