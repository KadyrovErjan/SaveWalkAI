# Реальные ширины объектов в метрах
REAL_WIDTH_M = {
    "person":        0.5,
    "cell phone":    0.07,
    "traffic light": 0.3,
}

# Калибровка: поставь человека на 2.0м, замерь pixel_w bounding box
# FOCAL_LENGTH = (pixel_w * 2.0) / 0.5
FOCAL_LENGTH = 700

def raw_distance(label: str, box: tuple):
    x1, y1, x2, y2 = box
    pixel_w = x2 - x1
    if pixel_w <= 0 or label not in REAL_WIDTH_M:
        return None
    return (REAL_WIDTH_M[label] * FOCAL_LENGTH) / pixel_w