REAL_WIDTH_M = {
    "person":        0.45,
    "car":           1.8,
    "traffic light": 0.25,
    "stop sign":     0.6,
    "bus":           2.5,
    "train":         3.0,
    "motorcycle":    0.7,
    "bicycle":       0.5,
}

# Калибровка: поставь человека на 2.0м, замерь pixel_w bbox,
# FOCAL_LENGTH = (pixel_w * 2.0) / 0.45
FOCAL_LENGTH = 756

def estimate_distance(label: str, box: tuple) -> float | None:
    x1, y1, x2, y2 = box
    pixel_w = x2 - x1
    if pixel_w <= 0:
        return None
    real_w = REAL_WIDTH_M.get(label)
    if real_w is None:
        return None
    return round((real_w * FOCAL_LENGTH) / pixel_w, 2)