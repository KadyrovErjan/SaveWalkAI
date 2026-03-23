import time
import logging
import cv2

from camera        import get_frame, release
from detection     import detect
from distance      import raw_distance
from sound_manager import SoundManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

# YOLO запускается раз в N кадров.
# 1 = каждый кадр (точнее, медленнее)
# 2 = через кадр (+35-40% FPS)
YOLO_EVERY_N = 2

sound_mgr   = SoundManager()
frame_count = 0
prev_dets   = []
t_prev      = time.monotonic()

print("SaveWalk AI запущен. Нажми Q для выхода.")

while True:
    frame = get_frame()
    if frame is None:
        print("Камера не отвечает.")
        break

    frame_count += 1

    if frame_count % YOLO_EVERY_N == 0:
        prev_dets = detect(frame)

    detections = prev_dets
    active_ids = set()

    for obj in detections:
        track_id = obj["track_id"]
        label    = obj["label"]
        box      = obj["box"]
        conf     = obj["conf"]

        if track_id is not None:
            active_ids.add(track_id)

        dist = raw_distance(label, box)

        # вся логика антиспама, сглаживания и озвучки — внутри process()
        sound_mgr.process(track_id, label, dist)

        # отрисовка
        x1, y1, x2, y2 = box
        dist_str  = f"{dist:.1f}m" if dist else "?m"
        color     = (0, 0, 255) if (dist and dist < 4.0) else (0, 200, 0)
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