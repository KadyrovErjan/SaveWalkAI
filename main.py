import time
import cv2

from camera import get_frame, show_frame, release, draw_fps
from detection import detect
from distance import get_distance
from voice import speak

# Расстояние (в метрах) при котором включается голосовое оповещение
ALERT_DISTANCE = 3.0

print("SaveWalk AI запущен. Нажмите 'Q' для выхода.")

while True:
    start_time = time.time()

    frame = get_frame()
    if frame is None:
        print("Ошибка: камера не даёт изображение.")
        break

    detections = detect(frame)

    for obj in detections:
        label = obj["label"]
        box = obj["box"]
        conf = obj["conf"]

        x1, y1, x2, y2 = box

        distance = get_distance(label, box)

        # Цвет рамки: красный если близко, зелёный если далеко
        color = (0, 0, 255) if (distance and distance < ALERT_DISTANCE) else (0, 255, 0)

        # Рисуем bounding box
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

        # Текст: название + дистанция + уверенность
        if distance:
            text = f"{label} {distance}m ({conf:.0%})"
        else:
            text = f"{label} ({conf:.0%})"

        # Фон под текстом для читаемости
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        cv2.rectangle(frame, (x1, y1 - th - 14), (x1 + tw + 4, y1), color, -1)
        cv2.putText(frame,
                    text,
                    (x1 + 2, y1 - 6),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 255),
                    2)

        # Голосовое оповещение если объект близко
        if distance and distance < ALERT_DISTANCE:
            speak(label, distance)

    # FPS
    fps = 1.0 / (time.time() - start_time + 1e-6)
    draw_fps(frame, fps)

    show_frame(frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

release()
print("Программа завершена.")