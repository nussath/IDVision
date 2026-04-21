import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY is not set. Copy .env.example to .env and fill in a random value."
    )

DB_PATH = os.environ.get("DB_PATH", "surveillance.db")
CAMERA_INDEX = int(os.environ.get("CAMERA_INDEX", "0"))
SESSION_MAX_AGE_MINUTES = int(os.environ.get("SESSION_MAX_AGE_MINUTES", "60"))
MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_MB", "5")) * 1024 * 1024

LBPH_MODEL_PATH = os.environ.get("LBPH_MODEL_PATH", "lbph_model.yml")
LABEL_MAP_PATH = os.environ.get("LABEL_MAP_PATH", "label_map.npy")
PERSONS_JSON_PATH = os.environ.get("PERSONS_JSON_PATH", "persons.json")
ALERT_COOLDOWN_SECONDS = float(os.environ.get("ALERT_COOLDOWN_SECONDS", "30"))
LBPH_CONFIDENCE_THRESHOLD = float(os.environ.get("LBPH_CONFIDENCE_THRESHOLD", "70"))
RECOGNITION_STREAK_WINDOW = int(os.environ.get("RECOGNITION_STREAK_WINDOW", "5"))
RECOGNITION_STREAK_REQUIRED = int(os.environ.get("RECOGNITION_STREAK_REQUIRED", "3"))

INITIAL_ADMIN_USERNAME = os.environ.get("INITIAL_ADMIN_USERNAME", "").strip()
INITIAL_ADMIN_PASSWORD = os.environ.get("INITIAL_ADMIN_PASSWORD", "")

DATASET_DIR = Path("dataset")
FACE_DETECTOR_MODEL_PATH = "face_detection_yunet_2023mar.onnx"
ALLOWED_ROLES = {"admin", "viewer"}
