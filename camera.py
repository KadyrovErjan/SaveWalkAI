import cv2

cap = cv2.VideoCapture(0)

def get_frame():
    ret, frame = cap.read()
    if not ret:
        return None
    return frame

def draw_fps(frame, fps):
    cv2.putText(frame,
                f'FPS: {fps:.1f}',
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2)

def show_frame(frame):
    cv2.imshow("SaveWalk AI", frame)

def release():
    cap.release()
    cv2.destroyAllWindows()