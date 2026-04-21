import os
import re

ALLOWED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_MB", "5")) * 1024 * 1024

_MAGIC_SIGNATURES = [
    (b"\xff\xd8\xff", "jpeg"),
    (b"\x89PNG\r\n\x1a\n", "png"),
    (b"RIFF", "webp"),  # WEBP files start with RIFF....WEBP; checked more strictly below
]


class ImageValidationError(ValueError):
    pass


def _looks_like_image(head: bytes) -> bool:
    if head.startswith(b"\xff\xd8\xff"):
        return True
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return True
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return True
    return False


def validate_image_bytes(data: bytes, filename: str = ""):
    """Raise ImageValidationError if data doesn't look like a supported image.
    Returns the detected extension (with leading dot)."""
    if not data:
        raise ImageValidationError("Empty file.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise ImageValidationError(
            f"File too large ({len(data)} bytes; max {MAX_UPLOAD_BYTES})."
        )

    ext = os.path.splitext(filename)[1].lower()
    if ext and ext not in ALLOWED_IMAGE_EXTS:
        raise ImageValidationError(
            f"Unsupported extension '{ext}'. Allowed: {sorted(ALLOWED_IMAGE_EXTS)}."
        )

    if not _looks_like_image(data[:16]):
        raise ImageValidationError("File does not look like a JPEG/PNG/WEBP image.")

    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    return ".webp"


_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def safe_filename(name: str) -> str:
    """Strip path separators and dodgy chars. Fallback to 'unnamed'."""
    name = os.path.basename(name or "").strip()
    name = _SAFE_NAME_RE.sub("_", name).strip("._")
    return name or "unnamed"


def person_folder(person_id: int, name: str) -> str:
    """Return a folder name like '3_Shreya' — matches the legacy label format."""
    return f"{int(person_id)}_{safe_filename(name)}"
