import os
import time
import random
import threading
import logging
from collections import deque

log = logging.getLogger(__name__)

# ─── аудио бэкенд ─────────────────────────────────────────────────────────────

def _init_backend():
    try:
        import simpleaudio as sa
        log.info("Аудио бэкенд: simpleaudio")
        return "simpleaudio", sa
    except ImportError:
        pass
    try:
        import pygame
        pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)
        log.info("Аудио бэкенд: pygame")
        return "pygame", pygame
    except ImportError:
        pass
    try:
        import winsound
        log.info("Аудио бэкенд: winsound")
        return "winsound", winsound
    except ImportError:
        pass
    log.warning("Аудио бэкенд не найден — только текстовый вывод")
    return None, None

_BACKEND, _LIB = _init_backend()

SOUNDS_DIR = "sounds"


def _find_wav(label: str, bucket: int):
    """
    Ищет sounds/<label>/<bucket>.wav
    Если точного нет — берёт ближайший меньший.
    Если совсем ничего — случайный из папки.
    """
    folder = os.path.join(SOUNDS_DIR, label)
    for d in range(bucket, 0, -1):
        path = os.path.join(folder, f"{d}.wav")
        if os.path.exists(path):
            return path
    if os.path.isdir(folder):
        wavs = [os.path.join(folder, f)
                for f in os.listdir(folder) if f.lower().endswith(".wav")]
        if wavs:
            return random.choice(wavs)
    return None


def _play_blocking(path: str, done_cb):
    """Воспроизводит wav синхронно. Вызывается только из daemon-треда."""
    try:
        if _BACKEND == "simpleaudio":
            wo = _LIB.WaveObject.from_wave_file(path)
            wo.play().wait_done()
        elif _BACKEND == "pygame":
            snd = _LIB.mixer.Sound(path)
            ch  = snd.play()
            while ch.get_busy():
                time.sleep(0.02)
        elif _BACKEND == "winsound":
            _LIB.PlaySound(path, _LIB.SND_FILENAME)
    except Exception as e:
        log.error("Ошибка воспроизведения %s: %s", path, e)
    finally:
        done_cb()


# ─── DistanceSmoother ─────────────────────────────────────────────────────────

HYSTERESIS = 0.15

class DistanceSmoother:
    def __init__(self, window: int = 5):
        self._window      = window
        self._bufs        = {}
        self._last_bucket = {}

    def update(self, track_id: int, raw: float):
        if track_id not in self._bufs:
            self._bufs[track_id] = deque(maxlen=self._window)

        self._bufs[track_id].append(raw)
        smoothed = sum(self._bufs[track_id]) / len(self._bufs[track_id])
        prev     = self._last_bucket.get(track_id)

        if prev is None:
            bucket = int(smoothed)
            self._last_bucket[track_id] = bucket
            return round(smoothed, 2), bucket, False

        candidate = int(smoothed)

        if candidate > prev:
            new_bucket = candidate
        elif candidate < prev:
            if smoothed < (prev - HYSTERESIS):
                new_bucket = candidate
            else:
                new_bucket = prev
        else:
            new_bucket = prev

        changed = new_bucket != prev
        if changed:
            self._last_bucket[track_id] = new_bucket

        return round(smoothed, 2), new_bucket, changed

    def remove(self, track_id: int):
        self._bufs.pop(track_id, None)
        self._last_bucket.pop(track_id, None)

    def cleanup(self, active_ids: set):
        for tid in list(self._bufs):
            if tid not in active_ids:
                self.remove(tid)


# ─── SoundManager ─────────────────────────────────────────────────────────────

class SoundManager:
    TRIGGER_CLASSES = {"person"}
    MAX_DIST_M      = 5.0
    STABLE_FRAMES   = 3
    COOLDOWN_SEC    = 4.0
    RETRIGGER_AFTER = 6.0
    MISSING_RESET   = 5

    def __init__(self):
        self.smoother = DistanceSmoother(window=5)

        self._lock    = threading.Lock()
        self._playing = False

        self._last_played  = {}
        self._last_bucket  = {}
        self._last_seen    = {}
        self._consec       = {}
        self._missing      = {}

    # ──────────────────────────────────────────────────────────────────────────
    # НОВЫЙ МЕТОД: прямое воспроизведение любого wav-файла (для светофора и др.)
    # Не блокирует main loop, не мешает звукам person.
    # ──────────────────────────────────────────────────────────────────────────
    def play_file(self, path: str):
        """
        Воспроизводит wav по прямому пути без антиспама и bucket-логики.
        Используется для светофора: play_file("sounds/traffic light/red.wav")
        Если сейчас уже играет другой звук — ждёт своей очереди.
        """
        if not os.path.exists(path):
            log.warning("[play_file] Файл не найден: %s", path)
            return

        def _worker():
            # Ждём пока освободится канал (не бесконечно — макс 3 сек)
            deadline = time.monotonic() + 3.0
            while time.monotonic() < deadline:
                with self._lock:
                    if not self._playing:
                        self._playing = True
                        break
                time.sleep(0.05)
            else:
                log.debug("[play_file] Пропущен (канал занят): %s", path)
                return

            log.info("[СВЕТОФОР] ▶ %s", path)
            _play_blocking(path, self._on_done)

        threading.Thread(target=_worker, daemon=True).start()

    # ──────────────────────────────────────────────────────────────────────────

    def process(self, track_id, label, raw_distance):
        if track_id is None or raw_distance is None:
            return

        now = time.monotonic()

        self._missing[track_id]   = 0
        self._consec[track_id]    = self._consec.get(track_id, 0) + 1
        self._last_seen[track_id] = now

        smoothed, bucket, bucket_changed = self.smoother.update(track_id, raw_distance)

        if label not in self.TRIGGER_CLASSES:
            return
        if smoothed >= self.MAX_DIST_M:
            return
        if bucket == 0:
            return
        if self._consec[track_id] < self.STABLE_FRAMES:
            return

        gap = now - self._last_played.get(track_id, 0)
        if gap >= self.RETRIGGER_AFTER:
            self._last_bucket.pop(track_id, None)
            bucket_changed = True

        if not bucket_changed:
            return
        if self._last_bucket.get(track_id) == bucket:
            return
        if now - self._last_played.get(track_id, 0) < self.COOLDOWN_SEC:
            return

        with self._lock:
            if self._playing:
                return
            path = _find_wav(label, bucket)
            if path is None:
                log.debug("wav не найден: sounds/%s/%d.wav", label, bucket)
                return
            self._playing = True

        self._last_played[track_id] = now
        self._last_bucket[track_id] = bucket

        log.info("[ЗВУК] %s #%d  %.2fm → bucket=%d  (%s)",
                 label, track_id, smoothed, bucket, path)

        threading.Thread(
            target=_play_blocking,
            args=(path, self._on_done),
            daemon=True,
        ).start()

    def tick_missing(self, active_ids: set):
        for tid in list(self._consec):
            if tid not in active_ids:
                self._missing[tid] = self._missing.get(tid, 0) + 1
                if self._missing[tid] >= self.MISSING_RESET:
                    self._consec.pop(tid, None)
                    self._missing.pop(tid, None)

        threshold = time.monotonic() - self.RETRIGGER_AFTER * 3
        for tid in list(self._last_seen):
            if self._last_seen[tid] < threshold and tid not in active_ids:
                self._last_played.pop(tid, None)
                self._last_bucket.pop(tid, None)
                self._last_seen.pop(tid, None)

        self.smoother.cleanup(active_ids)

    def _on_done(self):
        with self._lock:
            self._playing = False