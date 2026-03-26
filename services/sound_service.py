"""
SoundService v2.0
-----------------
Логика воспроизведения звуков для SaveWalk AI.

Правила:
  1. Только один объект озвучивается за раз (top_threat).
  2. Высокий риск → только alert, остальное пропускается.
  3. Звуки объекта воспроизводятся последовательно через очередь:
       direction → dist → motion
  4. Cooldown на track_id: один объект не чаще раз в COOLDOWN_SEC.
  5. Навигация: если top_threat по центру и близко → go_left / go_right.
  6. Никаких time.sleep — всё через threading + очередь.
"""

import os
import time
import queue
import threading
import logging

log = logging.getLogger(__name__)

# ─── Пути к звукам ────────────────────────────────────────────────────────────

SOUNDS = "sounds"

def _p(*parts) -> str:
    """Собирает путь и возвращает только если файл существует."""
    path = os.path.join(SOUNDS, *parts)
    return path if os.path.exists(path) else None


def _dist_file(label: str, dist: float) -> str | None:
    """sounds/<label>/dist/N.wav — N = 1..5 по округлению."""
    bucket = max(1, min(5, int(dist)))
    return _p(label, "dist", f"{bucket}.wav")


# ─── Настройки ────────────────────────────────────────────────────────────────

COOLDOWN_SEC    = 2.5    # один track_id не чаще раз в N сек
HIGH_RISK_SCORE = 15.0   # выше этого → только alert, без остального
NAV_DIST_M      = 2.5    # ближе этого + центр → навигационная подсказка

# Звуки светофора
TL_SOUND = {
    "red":    _p("traffic light", "red.wav"),
    "green":  _p("traffic light", "green.wav"),
    "yellow": _p("traffic light", "yellow.wav"),
}
TL_COOLDOWN_SEC = 5.0


# ─── Очередь последовательного воспроизведения ────────────────────────────────

class _SequentialPlayer:
    """
    Принимает список wav-файлов и воспроизводит их один за другим
    через sound_manager.play_file(), не блокируя main loop.
    """

    def __init__(self, sound_manager):
        self._mgr   = sound_manager
        self._queue: queue.Queue = queue.Queue()
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def play_sequence(self, paths: list[str]):
        """Добавить новую последовательность (старая прерывается через очистку)."""
        # Чистим предыдущую очередь — новый объект важнее
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break
        for p in paths:
            if p:  # None-пути пропускаем
                self._queue.put(p)

    def _worker(self):
        while True:
            path = self._queue.get()   # блокирует до появления задачи
            if not os.path.exists(path):
                log.debug("[sound] файл не найден: %s", path)
                continue
            # play_file сам ждёт освобождения канала
            self._mgr.play_file(path)
            # Небольшая пауза между звуками в последовательности
            time.sleep(0.15)


# ─── SoundService ─────────────────────────────────────────────────────────────

class SoundService:

    def __init__(self, sound_manager):
        self._mgr     = sound_manager
        self._player  = _SequentialPlayer(sound_manager)

        # Антиспам: track_id → время последнего воспроизведения
        self._last_played:  dict[int, float] = {}
        # Светофор: track_id → (color, time)
        self._tl_last: dict[int, tuple[str, float]] = {}

    # ── Публичный API ─────────────────────────────────────────────────────────

    def process_threat(self, top_threat: dict | None, all_objects: list[dict]):
        """
        Главный метод — вызывать из main loop для каждого кадра.
        top_threat — результат pick_top_threat().
        all_objects — все enriched объекты (для навигации).
        """
        if top_threat is None:
            return

        track_id = top_threat.get("track_id")
        if track_id is None:
            return

        # Cooldown
        now = time.monotonic()
        if now - self._last_played.get(track_id, 0) < COOLDOWN_SEC:
            return

        sequence = self._build_sequence(top_threat, all_objects)
        if not sequence:
            return

        self._last_played[track_id] = now
        log.info(
            "[SOUND] %s #%d | risk=%.1f | seq=%s",
            top_threat["label"], track_id,
            top_threat.get("risk", 0),
            [os.path.basename(p) for p in sequence],
        )
        self._player.play_sequence(sequence)

    def process_traffic_light(self, track_id: int | None, tl_color: str | None):
        """Озвучивает светофор при смене цвета или по таймеру."""
        if tl_color is None or track_id is None:
            return

        last_color, last_time = self._tl_last.get(track_id, (None, 0.0))
        now = time.monotonic()

        if tl_color == last_color and (now - last_time) < TL_COOLDOWN_SEC:
            return

        path = TL_SOUND.get(tl_color)
        if path:
            self._mgr.play_file(path)
            log.info("[СВЕТОФОР] #%d  %s", track_id, tl_color)
        self._tl_last[track_id] = (tl_color, now)

    # ── Построение последовательности ────────────────────────────────────────

    def _build_sequence(self, obj: dict, all_objects: list[dict]) -> list[str]:
        label     = obj.get("label", "")
        dist      = obj.get("dist")
        direction = obj.get("direction", "center")
        motion    = obj.get("motion",    "stable")
        risk      = obj.get("risk",      0.0)

        if dist is None:
            return []

        # ── Высокий риск → только alert ──────────────────────────────────────
        if risk >= HIGH_RISK_SCORE:
            if dist <= 1.5:
                alert = _p(label, "alert", "very_close.wav") \
                     or _p("alerts", "very_close.wav")
            else:
                alert = _p(label, "alert", "danger.wav") \
                     or _p("alerts", "danger.wav")
            return [alert] if alert else []

        # ── Навигация: центр + близко ─────────────────────────────────────────
        if direction == "center" and dist <= NAV_DIST_M:
            nav = self._nav_sound(all_objects)
            if nav:
                obstacle = _p("navigation", "obstacle.wav")
                return [p for p in [obstacle, nav] if p]

        # ── Стандартная последовательность ───────────────────────────────────
        # direction → dist → motion
        seq = []

        dir_sound = _p(label, "direction", f"{direction}.wav")
        if not dir_sound:
            dir_sound = _p("person", "direction", f"{direction}.wav")  # fallback
        if dir_sound:
            seq.append(dir_sound)

        dist_sound = _dist_file(label, dist)
        if not dist_sound:
            dist_sound = _dist_file("person", dist)  # fallback
        if dist_sound:
            seq.append(dist_sound)

        motion_sound = _p(label, "motion", f"{motion}.wav")
        if not motion_sound:
            motion_sound = _p("person", "motion", f"{motion}.wav")  # fallback
        if motion_sound:
            seq.append(motion_sound)

        return seq

    def _nav_sound(self, all_objects: list[dict]) -> str | None:
        """Выбирает свободную сторону и возвращает go_left / go_right."""
        occupied = {o.get("direction") for o in all_objects}
        if "left" not in occupied:
            return _p("navigation", "go_left.wav")
        if "right" not in occupied:
            return _p("navigation", "go_right.wav")
        return _p("navigation", "go_straight.wav")