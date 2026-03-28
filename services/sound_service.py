"""
SoundService v4.0 — Навигационный ассистент
--------------------------------------------
Принцип: не описывать объекты, а помогать двигаться.

Логика решений:
  STOP      → объект ближе VERY_CLOSE_M (любой класс)
  DANGER    → машина/мотоцикл приближается < DANGER_DIST_M
  PERSON    → человек по центру + approaching → person_ahead → обход
  NAVIGATE  → объект по центру → left.wav / right.wav (свободная сторона)
  GO        → путь свободен → go.wav (не чаще раза в GO_INTERVAL сек)

Приоритет сигналов (сверху вниз, первый подходящий):
  1. stop / very_close    — немедленная опасность
  2. car / bus / moto     — транспорт приближается
  3. person_ahead         — человек по центру
  4. navigate (обход)     — предложить сторону
  5. go                   — путь свободен
"""

import os
import time
import threading
import logging

log = logging.getLogger(__name__)

# ─── Пути ─────────────────────────────────────────────────────────────────────
SOUNDS_DIR = "sounds"

def _s(*parts) -> str | None:
    p = os.path.join(SOUNDS_DIR, *parts)
    return p if os.path.exists(p) else None

# Все звуки навигации
class S:
    GO           = _s("system", "go.wav")
    STOP         = _s("system", "stop.wav")
    LEFT         = _s("system", "left.wav")
    RIGHT        = _s("system", "right.wav")
    VERY_CLOSE   = _s("system", "very_close.wav")
    PERSON_AHEAD = _s("system", "person_ahead.wav")
    OBSTACLE     = _s("system", "obstacle.wav")
    NO_WAY       = _s("system", "no_way.wav")

    TL_RED       = _s("traffic light", "red.wav")
    TL_GREEN     = _s("traffic light", "green.wav")
    TL_YELLOW    = _s("traffic light", "yellow.wav")

# ─── Настройки ────────────────────────────────────────────────────────────────

VERY_CLOSE_M  = 1.0    # ближе → немедленный stop
DANGER_DIST_M = 2.5    # транспорт ближе → danger
PERSON_DIST_M = 2.0    # человек по центру ближе → person_ahead
NAV_DIST_M    = 3.5    # объект по центру ближе → предложить обход

COOLDOWN_SEC  = 2.5    # минимальный интервал между любыми звуками
GO_INTERVAL   = 5.0    # "go" не чаще раза в N сек
TL_COOLDOWN   = 5.0    # светофор не чаще раза в N сек

# Транспорт — высокая опасность
TRANSPORT = {"car", "bus", "motorcycle", "bicycle", "train"}

# Всё что является препятствием
OBSTACLES = {"car", "bus", "motorcycle", "bicycle", "train", "person", "stop sign"}

# ─── Аудио бэкенд ─────────────────────────────────────────────────────────────

def _build_play_fn():
    try:
        import simpleaudio as sa
        def play(path):
            sa.WaveObject.from_wave_file(path).play().wait_done()
        log.info("Аудио: simpleaudio")
        return play
    except ImportError:
        pass
    try:
        import pygame
        pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)
        def play(path):
            snd = pygame.mixer.Sound(path)
            ch  = snd.play()
            while ch.get_busy():
                time.sleep(0.02)
        log.info("Аудио: pygame")
        return play
    except ImportError:
        pass
    try:
        import winsound
        def play(path):
            winsound.PlaySound(path, winsound.SND_FILENAME)
        log.info("Аудио: winsound")
        return play
    except ImportError:
        pass
    log.warning("Аудио бэкенд не найден")
    return None

_PLAY_FN = _build_play_fn()


class _Player:
    """Один звук в один момент времени. Не блокирует main loop."""

    def __init__(self):
        self._lock    = threading.Lock()
        self._playing = False

    @property
    def busy(self) -> bool:
        with self._lock:
            return self._playing

    def play(self, path: str) -> bool:
        if not path or not os.path.exists(path):
            log.debug("[player] файл не найден: %s", path)
            return False
        with self._lock:
            if self._playing or _PLAY_FN is None:
                return False
            self._playing = True
        threading.Thread(target=self._worker, args=(path,), daemon=True).start()
        return True

    def _worker(self, path):
        try:
            _PLAY_FN(path)
        except Exception as e:
            log.error("Ошибка воспроизведения %s: %s", path, e)
        finally:
            with self._lock:
                self._playing = False


# ─── SoundService ─────────────────────────────────────────────────────────────

class SoundService:
    """
    Навигационный ассистент звука.

    Использование в main.py:
        sound_svc = SoundService()

        # каждый кадр:
        sound_svc.update(enriched_objs, top_threat)

        # для светофора:
        sound_svc.traffic_light(track_id, color)
    """

    def __init__(self):
        self._player     = _Player()
        self._last_sound: str | None = None        # последний сыгранный файл
        self._last_time:  float      = 0.0         # время последнего звука
        self._last_go:    float      = 0.0         # время последнего "go"
        self._tl_state:   dict       = {}           # track_id → (color, time)

    # ── Главный метод — вызывать каждый кадр ─────────────────────────────────

    def update(self, all_objects: list[dict], top_threat: dict | None):
        """
        all_objects — все enriched объекты кадра (для определения свободных сторон).
        top_threat  — результат pick_top_threat() — самый опасный объект.
        """
        now = time.monotonic()

        # Глобальный cooldown — не чаще COOLDOWN_SEC
        if now - self._last_time < COOLDOWN_SEC:
            return

        # Канал занят — ждём
        if self._player.busy:
            return

        sound = self._decide(all_objects, top_threat, now)
        if sound is None:
            return

        # Не повторять тот же звук подряд (кроме stop — он всегда важен)
        if sound == self._last_sound and sound != S.STOP:
            return

        if self._player.play(sound):
            self._last_sound = sound
            self._last_time  = now
            if sound == S.GO:
                self._last_go = now
            log.info("[NAV] %s", os.path.basename(sound))

    # ── Светофор ──────────────────────────────────────────────────────────────

    def traffic_light(self, track_id: int | None, color: str | None):
        """Озвучивает светофор при смене цвета или по таймеру."""
        if color is None or track_id is None:
            return

        now = time.monotonic()
        last_color, last_time = self._tl_state.get(track_id, (None, 0.0))

        if color == last_color and (now - last_time) < TL_COOLDOWN:
            return

        path = {
            "red":    S.TL_RED,
            "green":  S.TL_GREEN,
            "yellow": S.TL_YELLOW,
        }.get(color)

        if self._player.play(path):
            self._tl_state[track_id] = (color, now)
            self._last_time = now
            log.info("[TL] #%d %s", track_id, color)

    # ── Логика принятия решений ────────────────────────────────────────────────

    def _decide(self, all_objects: list[dict], top: dict | None, now: float) -> str | None:

        # ── Приоритет 1: НЕМЕДЛЕННАЯ ОПАСНОСТЬ — очень близко ────────────────
        very_close = self._find(all_objects,
            lambda o: o.get("dist", 99) <= VERY_CLOSE_M
        )
        if very_close:
            return S.STOP or S.VERY_CLOSE

        # ── Приоритет 2: ТРАНСПОРТ приближается ──────────────────────────────
        danger = self._find(all_objects,
            lambda o: (
                o.get("label") in TRANSPORT
                and o.get("motion") == "approaching"
                and o.get("dist", 99) <= DANGER_DIST_M
            )
        )
        if danger:
            # Если по центру → предложить обход, иначе просто сигнал
            if danger.get("direction") == "center":
                free = self._free_side(all_objects)
                return free or S.NO_WAY or S.OBSTACLE
            else:
                return S.OBSTACLE

        # ── Приоритет 3: ЧЕЛОВЕК по центру + приближается ────────────────────
        person_center = self._find(all_objects,
            lambda o: (
                o.get("label") == "person"
                and o.get("direction") == "center"
                and o.get("motion") == "approaching"
                and o.get("dist", 99) <= PERSON_DIST_M
            )
        )
        if person_center:
            return S.PERSON_AHEAD or S.OBSTACLE

        # ── Приоритет 4: ЛЮБОЙ объект по центру + близко ─────────────────────
        center_obj = self._find(all_objects,
            lambda o: (
                o.get("direction") == "center"
                and o.get("dist", 99) <= NAV_DIST_M
                and o.get("label") in OBSTACLES
            )
        )
        if center_obj:
            free = self._free_side(all_objects)
            return free or S.NO_WAY

        # ── Приоритет 5: ПУТЬ СВОБОДЕН → go (не чаще GO_INTERVAL) ───────────
        if (now - self._last_go) >= GO_INTERVAL:
            center_blocked = any(
                o.get("direction") == "center" and o.get("dist", 99) <= NAV_DIST_M
                for o in all_objects
            )
            if not center_blocked:
                return S.GO

        return None

    # ── Вспомогательные ───────────────────────────────────────────────────────

    @staticmethod
    def _find(objects: list[dict], condition) -> dict | None:
        """Возвращает первый объект удовлетворяющий условию (по убыванию risk)."""
        candidates = [o for o in objects if condition(o)]
        if not candidates:
            return None
        return max(candidates, key=lambda o: o.get("risk", 0))

    @staticmethod
    def _free_side(objects: list[dict]) -> str | None:
        """Возвращает звук для свободной стороны (left/right)."""
        occupied = {o.get("direction") for o in objects}
        if "left" not in occupied:
            return S.LEFT
        if "right" not in occupied:
            return S.RIGHT
        return None