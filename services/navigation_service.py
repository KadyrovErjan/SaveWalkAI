"""
Простая навигационная логика:
- делит кадр на 3 зоны: left / center / right
- если центр занят — предлагает свободную сторону
"""

FRAME_W = 640


def get_free_side(objects: list[dict]) -> str | None:
    """
    objects — список активных объектов с полем 'direction'.
    Возвращает 'left' / 'right' / None (если путь свободен).
    """
    occupied = {obj.get("direction") for obj in objects}

    if "center" not in occupied:
        return None   # центр свободен — идти прямо

    # Ищем свободную сторону
    if "left" not in occupied:
        return "left"
    if "right" not in occupied:
        return "right"

    return None   # всё занято — просто предупреждаем


def navigation_hint(objects: list[dict], top_threat: dict | None) -> str | None:
    """
    Возвращает текстовую подсказку для лога/дисплея.
    Например: "obstacle ahead → go right"
    """
    if top_threat is None:
        return None

    direction = top_threat.get("direction", "center")
    dist      = top_threat.get("dist")
    label     = top_threat.get("label", "object")
    dist_str  = f"{dist:.1f}m" if dist else "?m"

    if direction == "center":
        free = get_free_side(objects)
        if free:
            return f"obstacle ahead {dist_str} → move {free}"
        else:
            return f"obstacle ahead {dist_str} → stop"
    elif direction == "left":
        return f"{label} on left {dist_str}"
    else:
        return f"{label} on right {dist_str}"