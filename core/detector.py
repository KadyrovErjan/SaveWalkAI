from ultralytics import YOLO

model = YOLO("../yolov8n.pt")

TRACKED_CLASSES = {
    "person", "car", "traffic light", "stop sign",
    "train", "bus", "motorcycle", "bicycle",
}


def detect(frame):
    """Запускает YOLO + ByteTrack, возвращает список объектов."""
    results = model.track(
        frame,
        conf=0.45,
        iou=0.5,
        persist=True,
        tracker="bytetrack.yaml",
        verbose=False,
        imgsz=640,
    )
    detections = []
    for r in results:
        if r.boxes is None:
            continue
        for box in r.boxes:
            label = model.names[int(box.cls[0])]
            if label not in TRACKED_CLASSES:
                continue
            track_id = int(box.id[0]) if box.id is not None else None
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            detections.append({
                "label":    label,
                "box":      (x1, y1, x2, y2),
                "conf":     float(box.conf[0]),
                "track_id": track_id,
            })
    return detections