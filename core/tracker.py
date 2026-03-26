import time

# ─── EMA сглаживание расстояния ──────────────────────────────────────────────

EMA_ALPHA = 0.35   # чем меньше — тем плавнее, но медленнее реакция

class DistanceSmoother:
    def __init__(self):
        self._ema: dict[int, float] = {}   # track_id → сглаженное расстояние

    def update(self, track_id: int, raw: float) -> float:
        if track_id not in self._ema:
            self._ema[track_id] = raw
        else:
            self._ema[track_id] = EMA_ALPHA * raw + (1 - EMA_ALPHA) * self._ema[track_id]
        return round(self._ema[track_id], 2)

    def remove(self, track_id: int):
        self._ema.pop(track_id, None)

    def cleanup(self, active_ids: set):
        for tid in list(self._ema):
            if tid not in active_ids:
                self.remove(tid)


# ─── Направление объекта (left / center / right) ─────────────────────────────

FRAME_W = 640   # должно совпадать с camera.py

def get_direction(box: tuple) -> str:
    x1, y1, x2, y2 = box
    cx = (x1 + x2) / 2
    third = FRAME_W / 3
    if cx < third:
        return "left"
    elif cx > third * 2:
        return "right"
    else:
        return "center"


# ─── Движение объекта (approaching / leaving / stable) ───────────────────────

MOTION_WINDOW_SEC = 1.5   # анализируем изменение за последние N секунд
MOTION_THRESHOLD  = 0.3   # минимальное изменение расстояния для определения движения

class MotionTracker:
    def __init__(self):
        # track_id → [(timestamp, smoothed_dist), ...]
        self._history: dict[int, list] = {}

    def update(self, track_id: int, dist: float) -> str:
        """Возвращает: 'approaching', 'leaving', 'stable'."""
        now = time.monotonic()

        if track_id not in self._history:
            self._history[track_id] = []

        self._history[track_id].append((now, dist))

        # Убираем старые записи
        cutoff = now - MOTION_WINDOW_SEC
        self._history[track_id] = [
            (t, d) for t, d in self._history[track_id] if t >= cutoff
        ]

        history = self._history[track_id]
        if len(history) < 2:
            return "stable"

        oldest_dist = history[0][1]
        delta = oldest_dist - dist   # положительный = приближается

        if delta > MOTION_THRESHOLD:
            return "approaching"
        elif delta < -MOTION_THRESHOLD:
            return "leaving"
        else:
            return "stable"

    def remove(self, track_id: int):
        self._history.pop(track_id, None)

    def cleanup(self, active_ids: set):
        for tid in list(self._history):
            if tid not in active_ids:
                self.remove(tid)