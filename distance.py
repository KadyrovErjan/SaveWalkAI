# Реальные размеры объектов в метрах (ширина)
REAL_WIDTH = {
    "person": 0.5,
    "cell phone": 0.07,
    "traffic light": 0.3
}

FOCAL_LENGTH = 700  # подбирается экспериментально под вашу камеру

def get_distance(label, box):
    x1, y1, x2, y2 = box
    width_pixels = x2 - x1

    if label not in REAL_WIDTH or width_pixels == 0:
        return None

    real_width = REAL_WIDTH[label]
    distance = (real_width * FOCAL_LENGTH) / width_pixels

    return round(distance, 1)  # округляем до 1 знака