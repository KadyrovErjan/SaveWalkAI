import time
import logging
import cv2

from camera                      import get_frame, release
from core.detector               import detect
from core.distance               import estimate_distance
from core.tracker                import DistanceSmoother, MotionTracker, get_direction
from core.traffic_light          import detect_color
from services.danger_service     import calc_risk, pick_top_threat
from services.sound_service      import SoundService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

YOLO_EVERY_N  = 2
DANGER_DIST_M = 3.0

TL_BOX_COLOR = {
    "red":    (0,   0,   255),
    "green":  (0,   200, 0),
    "yellow": (0,   200, 255),
    None:     (180, 180, 180),
}

sound_svc  = SoundService()
smoother   = DistanceSmoother()
motion_trk = MotionTracker()

frame_count = 0
prev_dets   = []
t_prev      = time.monotonic()

print("SaveWalk AI v2.0 запущен. Нажми Q для выхода.")

while True:
    frame = get_frame()
    if frame is None:
        log.warning("Камера не отвечает.")
        break

    frame_count += 1
    if frame_count % YOLO_EVERY_N == 0:
        prev_dets = detect(frame)

    active_ids    = set()
    enriched_objs = []
    tl_objects    = []

    for obj in prev_dets:
        track_id = obj["track_id"]
        label    = obj["label"]
        box      = obj["box"]

        if track_id is not None:
            active_ids.add(track_id)

        if label == "traffic light":
            tl_objects.append(obj)
            continue

        raw_dist = estimate_distance(label, box)
        if raw_dist is None:
            continue

        dist      = smoother.update(track_id, raw_dist) if track_id else raw_dist
        direction = get_direction(box)
        motion    = motion_trk.update(track_id, dist) if track_id else "stable"
        risk      = calc_risk(label, dist, motion)

        enriched_objs.append({
            **obj,
            "dist":      dist,
            "direction": direction,
            "motion":    motion,
            "risk":      risk,
        })

        log.info("%s #%s | dist=%.2f | dir=%s | motion=%s | risk=%.1f",
                 label, track_id, dist, direction, motion, risk)

    # ── Навигационный звук ────────────────────────────────────────────────────
    top_threat = pick_top_threat(enriched_objs)
    sound_svc.update(enriched_objs, top_threat)   # ← один вызов, вся логика внутри

    # ── Светофоры ─────────────────────────────────────────────────────────────
    for tl in tl_objects:
        tl_color = detect_color(frame, tl["box"])
        sound_svc.traffic_light(tl["track_id"], tl_color)

        x1, y1, x2, y2 = tl["box"]
        color     = TL_BOX_COLOR.get(tl_color, TL_BOX_COLOR[None])
        label_str = f"TL #{tl['track_id']} [{tl_color or '?'}] {tl['conf']:.0%}"

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        (tw, th), _ = cv2.getTextSize(label_str, cv2.FONT_HERSHEY_SIMPLEX, 0.52, 2)
        cv2.rectangle(frame, (x1, y1 - th - 10), (x1 + tw + 6, y1), color, -1)
        cv2.putText(frame, label_str, (x1 + 3, y1 - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 2)

    # ── Отрисовка объектов ────────────────────────────────────────────────────
    for obj in enriched_objs:
        x1, y1, x2, y2 = obj["box"]
        dist   = obj["dist"]
        is_top = top_threat and obj["track_id"] == top_threat["track_id"]

        color = (255, 255, 255) if is_top else \
                (0, 0, 255)     if dist < DANGER_DIST_M else \
                (0, 200, 0)

        label_str = (f"{obj['label']} #{obj['track_id']}  "
                     f"{dist:.1f}m {obj['direction']} "
                     f"{obj['motion']}  r={obj['risk']:.0f}")

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        (tw, th), _ = cv2.getTextSize(label_str, cv2.FONT_HERSHEY_SIMPLEX, 0.48, 2)
        cv2.rectangle(frame, (x1, y1 - th - 10), (x1 + tw + 6, y1), color, -1)
        cv2.putText(frame, label_str, (x1 + 3, y1 - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 255, 255), 2)

    smoother.cleanup(active_ids)
    motion_trk.cleanup(active_ids)

    now    = time.monotonic()
    fps    = 1.0 / (now - t_prev + 1e-9)
    t_prev = now
    cv2.putText(frame, f"FPS: {fps:.1f}", (10, 28),
                cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 2)

    cv2.imshow("SaveWalk AI v2.0", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

release()
print("Завершено.")

