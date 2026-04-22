import time

import cv2

from . import config
from .utils import safe_filename


def save_snapshot(frame_bgr, name: str, category: str) -> str:
    """Write a JPEG of the current frame to SNAPSHOT_DIR and return its path
    (or empty string if encoding failed)."""
    config.SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    fname = f"{ts}_{safe_filename(name)}_{safe_filename(category)}.jpg"
    path = config.SNAPSHOT_DIR / fname
    ok, buf = cv2.imencode(".jpg", frame_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    if not ok:
        return ""
    path.write_bytes(buf.tobytes())
    return str(path)
