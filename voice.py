import os
import time
import threading

# Пытаемся использовать simpleaudio, если нет — pygame
try:
    import simpleaudio as sa
    USE_SA = True
except ImportError:
    USE_SA = False
    try:
        import pygame
        pygame.mixer.init()
        USE_PYGAME = True
    except ImportError:
        USE_PYGAME = False

# -----------------------------------------------------------
# Структура папки со звуками:
#
#   sounds/
#     person/
#       2.wav   (звук "1 метр")
#       2.wav   (звук "2 метра")
#       3.wav   ...
#     cell phone/
#       2.wav
#       2.wav
#     traffic light/
#       2.wav
#       2.wav
#
# Файлы называются по дистанции в метрах (целое число).
# -----------------------------------------------------------

SOUNDS_DIR = "sounds"

last_spoken = {}       # label -> время последнего озвучивания
COOLDOWN = 3           # секунды между повторными озвучками одного объекта


def _get_sound_file(label, distance):
    """Ищет подходящий wav-файл для объекта и дистанции."""
    dist_int = int(round(distance))           # округляем до целого метра
    dist_int = max(1, min(dist_int, 10))      # ограничиваем 1-10 метров

    folder = os.path.join(SOUNDS_DIR, label)
    path = os.path.join(folder, f"{dist_int}.wav")

    if os.path.exists(path):
        return path

    # Если точного файла нет — ищем ближайший
    for d in range(dist_int - 1, 0, -1):
        fallback = os.path.join(folder, f"{d}.wav")
        if os.path.exists(fallback):
            return fallback

    return None


def _play_file(path):
    """Воспроизводит wav-файл в отдельном потоке (не блокирует видео)."""
    def _run():
        if USE_SA:
            wave_obj = sa.WaveObject.from_wave_file(path)
            play_obj = wave_obj.play()
            play_obj.wait_done()
        elif USE_PYGAME:
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()
        else:
            # Крайний случай — системный playsound
            os.system(f'start "" "{path}"')  # Windows

    t = threading.Thread(target=_run, daemon=True)
    t.start()


def speak(label, distance):
    """Основная функция озвучки. Вызывается из main.py."""
    now = time.time()

    # Проверяем кулдаун
    if label in last_spoken and now - last_spoken[label] < COOLDOWN:
        return

    path = _get_sound_file(label, distance)

    if path is None:
        # Если wav-файлов нет — выводим в консоль
        print(f"[ГОЛОС] {label} — {distance} м")
        return

    print(f"[ГОЛОС] {label} — {distance} м → {path}")
    last_spoken[label] = now
    _play_file(path)