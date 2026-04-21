import cv2

from . import config
from .recognition import FaceRecognizer, log_alert, prepare_face

_camera = None
_face_detector = None
recognizer = FaceRecognizer()


def _init():
    global _camera, _face_detector
    if _camera is None:
        _camera = cv2.VideoCapture(config.CAMERA_INDEX, cv2.CAP_DSHOW)
    if _face_detector is None:
        _face_detector = cv2.FaceDetectorYN.create(
            config.FACE_DETECTOR_MODEL_PATH, "", (320, 320), 0.9, 0.3, 5000
        )
    return _camera, _face_detector


def reload_recognizer():
    """Re-instantiate the recogniser after training so new model is picked up."""
    global recognizer
    recognizer = FaceRecognizer()
    return recognizer


def gen_frames():
    camera, face_detector = _init()
    while True:
        success, frame = camera.read()
        if not success:
            break

        h, w = frame.shape[:2]
        face_detector.setInputSize((w, h))
        _, faces = face_detector.detect(frame)

        if faces is not None:
            for face in faces:
                x, y, bw, bh = face[:4].astype(int)
                x, y = max(0, x), max(0, y)
                bw, bh = max(1, bw), max(1, bh)

                label = "Face Detected"
                color = (0, 255, 0)

                gray_face = prepare_face(frame, x, y, bw, bh)
                if gray_face is not None:
                    name, category, _conf = recognizer.recognize(gray_face)
                    if name:
                        label = f"{name} ({category})"
                        color = (0, 0, 255) if category in ("criminal", "crime") else (0, 165, 255)
                        log_alert(name, category)
                    elif recognizer.ready:
                        label = "Unknown"
                        color = (0, 255, 255)

                cv2.rectangle(frame, (x, y), (x + bw, y + bh), color, 2)
                cv2.putText(frame, label, (x, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        ok, buffer = cv2.imencode(".jpg", frame)
        if not ok:
            continue
        yield (b"--frame\r\n"
               b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n")
