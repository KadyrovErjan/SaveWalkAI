# Базовый уровень риска по классу объекта
RISK_LEVEL = {
    "car":           10,
    "bus":           10,
    "train":         10,
    "motorcycle":    9,
    "bicycle":       6,
    "person":        3,
    "stop sign":     1,
    "traffic light": 0,   # светофор обрабатывается отдельно
}

# Дистанционные коэффициенты: чем ближе — тем выше риск
def _dist_multiplier(dist: float) -> float:
    if dist <= 1.0:   return 3.0
    elif dist <= 2.0: return 2.0
    elif dist <= 3.0: return 1.5
    elif dist <= 5.0: return 1.0
    else:             return 0.0   # дальше 5м — не озвучиваем

# Бонус если объект приближается
MOTION_BONUS = {
    "approaching": 1.5,
    "stable":      1.0,
    "leaving":     0.3,
}

MAX_DIST_M = 5.0


def calc_risk(label: str, dist: float, motion: str) -> float:
    """Возвращает числовой risk_score. 0 = не опасен."""
    if dist is None or dist > MAX_DIST_M:
        return 0.0
    base   = RISK_LEVEL.get(label, 0)
    result = base * _dist_multiplier(dist) * MOTION_BONUS.get(motion, 1.0)
    return round(result, 2)


def pick_top_threat(objects: list[dict]) -> dict | None:
    """
    Принимает список dict с полями: label, dist, motion, track_id, box, conf.
    Возвращает объект с наибольшим risk_score, или None если все risk=0.
    """
    best = None
    best_score = 0.0
    for obj in objects:
        score = calc_risk(obj["label"], obj.get("dist"), obj.get("motion", "stable"))
        obj["risk"] = score
        if score > best_score:
            best_score = score
            best = obj
    return best