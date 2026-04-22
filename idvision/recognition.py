import json
import threading
import time
from collections import deque
from pathlib import Path

import cv2
import numpy as np

from . import config
from .db import add_alert
from .notifications import send_alert_email

FACE_SIZE = 200


class FaceRecognizer:
    """LBPH recogniser with a per-label streak filter to suppress flickery false
    positives. If model assets are missing, `ready` is False and `recognize`
    always returns a no-match — callers can still run detect-only."""

    def __init__(self):
        self.ready = False
        self.model = None
        self.label_map = {}
        self.person_info = {}
        self._recent = deque(maxlen=max(1, config.RECOGNITION_STREAK_WINDOW))
        self._lock = threading.Lock()
        self._load()

    def _load(self):
        missing = [
            p for p in (config.LBPH_MODEL_PATH, config.LABEL_MAP_PATH, config.PERSONS_JSON_PATH)
            if not Path(p).exists()
        ]
        if missing:
            print(f"[recognition] Model assets missing: {missing}. "
                  "Detection-only mode. Run train_lbph.py to enable recognition.")
            return

        if not hasattr(cv2, "face"):
            print("[recognition] cv2.face unavailable — install opencv-contrib-python.")
            return

        self.model = cv2.face.LBPHFaceRecognizer_create()
        self.model.read(config.LBPH_MODEL_PATH)
        self.label_map = np.load(config.LABEL_MAP_PATH, allow_pickle=True).item()
        with open(config.PERSONS_JSON_PATH, "r") as f:
            for p in json.load(f):
                self.person_info[p["person_id"]] = p
        self.ready = True
        print(f"[recognition] Loaded LBPH model with {len(self.label_map)} labels.")

    def _record(self, label):
        with self._lock:
            self._recent.append(label)
            return self._recent.count(label) if label is not None else 0

    def _resolve_label(self, label):
        """Return (name, category) for a trained label. Supports both the new
        dict-valued label_map and the legacy string form (folder name only,
        with category derived from persons.json — had id-collision bugs)."""
        entry = self.label_map.get(label)
        if entry is None:
            return None, None
        if isinstance(entry, dict):
            return entry.get("name"), entry.get("category", "unknown")

        # Legacy format: entry is just the folder name string "<id>_<name>".
        # Fall back to persons.json but this path is ambiguous across tables.
        try:
            person_id_str, name = entry.split("_", 1)
            person_id = int(person_id_str)
        except (ValueError, IndexError):
            return None, None
        info = self.person_info.get(person_id)
        if not info:
            return None, None
        return info.get("name", name).strip(), info.get("category", "unknown")

    def recognize(self, gray_face):
        if not self.ready:
            return None, None, float("inf")

        label, confidence = self.model.predict(gray_face)

        if confidence >= config.LBPH_CONFIDENCE_THRESHOLD or label not in self.label_map:
            self._record(None)
            return None, None, confidence

        name, category = self._resolve_label(label)
        if not name:
            self._record(None)
            return None, None, confidence

        hits = self._record(label)
        if hits < config.RECOGNITION_STREAK_REQUIRED:
            return None, None, confidence

        return name, category, confidence


class AlertCooldown:
    def __init__(self, seconds=None):
        self.seconds = seconds if seconds is not None else config.ALERT_COOLDOWN_SECONDS
        self._last = {}
        self._lock = threading.Lock()

    def should_alert(self, name, category):
        key = (name, category)
        now = time.monotonic()
        with self._lock:
            last = self._last.get(key, 0)
            if now - last < self.seconds:
                return False
            self._last[key] = now
            return True


_cooldown = AlertCooldown()


def log_alert(name, category, snapshot_path=None, location=None, log_file="alerts_log.txt"):
    if not _cooldown.should_alert(name, category):
        return False
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    add_alert(name, category, snapshot_path=snapshot_path, location=location)
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            suffix = f" @ {location}" if location else ""
            f.write(f"{timestamp} - {name} - {category}{suffix}\n")
    except OSError as e:
        print(f"[recognition] Could not write alert log: {e}")
    send_alert_email(name, category, timestamp, location=location, snapshot_path=snapshot_path)
    return True


def prepare_face(frame_bgr, x, y, w, h, size=FACE_SIZE):
    fh, fw = frame_bgr.shape[:2]
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(fw, x + w), min(fh, y + h)
    if x1 - x0 < 10 or y1 - y0 < 10:
        return None
    gray = cv2.cvtColor(frame_bgr[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY)
    return cv2.resize(gray, (size, size))
