import time
import logging
import cv2

from camera         import get_frame, release
from detection      import detect
from distance       import estimate_distance
from sound_manager  import SoundManager
from traffic_light  import detect_traffic_light_color

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

YOLO_EVERY_N  = 2
DANGER_DIST_M = 3.0

# Цвет рамки светофора по цвету сигнала
TL_BOX_COLOR = {
    "red":    (0,   0,   255),
    "green":  (0,   200, 0),
    "yellow": (0,   200, 255),
    None:     (200, 200, 200),
}

# Звуковые файлы светофора
TL_SOUND = {
    "red":    r"sounds\traffic light\red.wav",
    "green":  r"sounds\traffic light\green.wav",
    "yellow": r"sounds\traffic light\yellow.wav",
}

# Антиспам: не повторять один и тот же цвет светофора чаще чем раз в N секунд
TL_REPEAT_INTERVAL = 5.0

# track_id → (последний цвет, время последнего звука)
tl_last: dict[int, tuple[str, float]] = {}

sound_mgr   = SoundManager()
frame_count = 0
prev_dets   = []
t_prev      = time.monotonic()

print("SaveWalk AI запущен. Нажми Q для выхода.")

while True:
    frame = get_frame()
    if frame is None:
        logging.warning("Камера не отвечает.")
        break

    frame_count += 1

    if frame_count % YOLO_EVERY_N == 0:
        prev_dets = detect(frame)

    active_ids = set()

    for obj in prev_dets:
        track_id = obj["track_id"]
        label    = obj["label"]
        box      = obj["box"]
        conf     = obj["conf"]

        if track_id is not None:
            active_ids.add(track_id)

        x1, y1, x2, y2 = box

        # ── Светофор ──────────────────────────────────────────────────────────
        if label == "traffic light":
            tl_color = detect_traffic_light_color(frame, box)

            # Звук — только если цвет изменился или прошло TL_REPEAT_INTERVAL
            if tl_color is not None and track_id is not None:
                last_color, last_time = tl_last.get(track_id, (None, 0.0))
                now = time.monotonic()
                color_changed = tl_color != last_color
                time_ok       = (now - last_time) >= TL_REPEAT_INTERVAL

                if color_changed or time_ok:
                    sound_path = TL_SOUND.get(tl_color)
                    if sound_path:
                        sound_mgr.play_file(sound_path)
                        logging.info(f"[СВЕТОФОР] #{track_id}  цвет={tl_color}  → {sound_path}")
                    tl_last[track_id] = (tl_color, now)

            # Отрисовка светофора
            color     = TL_BOX_COLOR.get(tl_color, TL_BOX_COLOR[None])
            color_str = tl_color if tl_color else "?"
            label_str = f"traffic light #{track_id}  [{color_str}]  {conf:.0%}"

            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            (tw, th), _ = cv2.getTextSize(label_str, cv2.FONT_HERSHEY_SIMPLEX, 0.52, 2)
            cv2.rectangle(frame, (x1, y1 - th - 10), (x1 + tw + 6, y1), color, -1)
            cv2.putText(frame, label_str, (x1 + 3, y1 - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 2)
            continue

        # ── Остальные объекты (person, car, ...) ─────────────────────────────
        dist = estimate_distance(label, box)
        sound_mgr.process(track_id, label, dist)

        dist_str  = f"{dist:.1f}m" if dist is not None else "?m"
        is_danger = dist is not None and dist < DANGER_DIST_M
        color     = (0, 0, 255) if is_danger else (0, 200, 0)
        label_str = f"{label} #{track_id}  {dist_str}  {conf:.0%}"

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        (tw, th), _ = cv2.getTextSize(label_str, cv2.FONT_HERSHEY_SIMPLEX, 0.52, 2)
        cv2.rectangle(frame, (x1, y1 - th - 10), (x1 + tw + 6, y1), color, -1)
        cv2.putText(frame, label_str, (x1 + 3, y1 - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 2)

    sound_mgr.tick_missing(active_ids)

    now    = time.monotonic()
    fps    = 1.0 / (now - t_prev + 1e-9)
    t_prev = now
    cv2.putText(frame, f"FPS: {fps:.1f}", (10, 28),
                cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 2)

    cv2.imshow("SaveWalk AI", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

release()
print("Завершено.")