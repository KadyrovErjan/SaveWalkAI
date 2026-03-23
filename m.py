import cv2
from ultralytics import YOLO

model = YOLO('yolo26n.pt')
classes = ['cell phone']

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print('Camera not found')
    exit()

while True:
    ret, frame = cap.read()
    if not ret:
        break

    for c in model(frame, conf=0.5):
        for i in c.boxes:
            label = model.names[int(i.cls[0])]
            if label not in classes:
                continue

            x1, y1, x2, y2 = map(int, i.xyxy[0])
            conf = i.conf[0] * 100

            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, f'{label} {conf:.1f}', (x1, y1-5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

    cv2.imshow('Video', frame)

    key = cv2.waitKey(1) & 0xFF

    if key == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
