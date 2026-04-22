import threading

import cv2

from . import config
from .recognition import FaceRecognizer, log_alert, prepare_face
from .snapshots import save_snapshot

_face_detector = None
_stop_event = threading.Event()  # when set, any active gen_frames exits
_active_streams_lock = threading.Lock()
_active_streams = 0

recognizer = FaceRecognizer()


def _get_detector():
    global _face_detector
    if _face_detector is None:
        _face_detector = cv2.FaceDetectorYN.create(
            config.FACE_DETECTOR_MODEL_PATH, "", (320, 320), 0.9, 0.3, 5000
        )
    return _face_detector


def reload_recognizer():
    """Re-instantiate the recogniser after training so new model is picked up."""
    global recognizer
    recognizer = FaceRecognizer()
    return recognizer


def stop_camera():
    """Signal all active gen_frames loops to exit cleanly."""
    _stop_event.set()


def start_camera():
    """Clear the stop flag so the next gen_frames call can open the camera."""
    _stop_event.clear()


def is_running():
    with _active_streams_lock:
        return _active_streams > 0 and not _stop_event.is_set()


def is_stopped():
    return _stop_event.is_set()


def _increment_streams():
    global _active_streams
    with _active_streams_lock:
        _active_streams += 1


def _decrement_streams():
    global _active_streams
    with _active_streams_lock:
        if _active_streams > 0:
            _active_streams -= 1


def gen_frames():
    """MJPEG generator. Opens the webcam on entry, releases it on exit so
    navigating away from /camera (or clicking Stop) frees the device."""
    if _stop_event.is_set():
        return

    camera = cv2.VideoCapture(config.CAMERA_INDEX, cv2.CAP_DSHOW)
    if not camera.isOpened():
        return

    _increment_streams()
    try:
        face_detector = _get_detector()
        while not _stop_event.is_set():
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
                        name, category, conf = recognizer.recognize(gray_face)
                        if name:
                            label = f"{name} ({category}) {conf:.0f}"
                            color = (0, 0, 255) if category in ("criminal", "crime") else (0, 165, 255)
                            cv2.rectangle(frame, (x, y), (x + bw, y + bh), color, 2)
                            cv2.putText(frame, label, (x, y - 10),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                            snapshot = save_snapshot(frame, name, category)
                            log_alert(name, category, snapshot_path=snapshot,
                                      location=config.CAMERA_LOCATION)
                            continue
                        elif recognizer.ready:
                            label = f"Unknown {conf:.0f}"
                            color = (0, 255, 255)

                    cv2.rectangle(frame, (x, y), (x + bw, y + bh), color, 2)
                    cv2.putText(frame, label, (x, y - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

            ok, buffer = cv2.imencode(".jpg", frame)
            if not ok:
                continue
            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n")
    finally:
        camera.release()
        _decrement_streams()
