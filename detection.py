from ultralytics import YOLO

model = YOLO('yolov8n.pt')  # используем yolov8n.pt — самая стабильная модель

# Классы которые хотим отслеживать
TRACKED_CLASSES = ['person', 'cell phone', 'traffic light']

def detect(frame):
    results = model(frame, conf=0.5, verbose=False)  # verbose=False убирает лишние логи

    detections = []

    for r in results:
        for box in r.boxes:
            label = model.names[int(box.cls[0])]

            if label not in TRACKED_CLASSES:
                continue

            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = float(box.conf[0])

            detections.append({
                "label": label,
                "box": (x1, y1, x2, y2),
                "conf": conf
            })

    return detections