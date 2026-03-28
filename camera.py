import cv2

cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1750)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 700)
cap.set(cv2.CAP_PROP_FPS,          30)
cap.set(cv2.CAP_PROP_BUFFERSIZE,   1)

if not cap.isOpened():
    raise RuntimeError("Не удалось открыть камеру")

def get_frame():
    ret, frame = cap.read()
    return frame if ret else None

def release():
    cap.release()
    cv2.destroyAllWindows()