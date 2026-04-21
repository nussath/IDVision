# IDVision

Face-recognition and ID-verification system for identifying criminals and missing persons from a live camera feed. Built with FastAPI, OpenCV (YuNet + LBPH), and SQLite.

## Features

- Login / registration with bcrypt-hashed passwords and session cookies.
- Dashboard with live webcam feed and YuNet face detection.
- CRUD for criminals and missing persons.
- Alert log written to SQLite and `alerts_log.txt`.
- LBPH model training pipeline against the `dataset/` folder.
- Basic liveness check (blur variance).

## Requirements

- Python 3.10+
- A webcam (for the live feed)
- Windows / macOS / Linux

Python packages are listed in `requirements.txt`.

## Setup

```bash
# 1. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
copy .env.example .env         # Windows
# cp .env.example .env         # macOS / Linux
# Edit .env and set SECRET_KEY. Optionally set INITIAL_ADMIN_USERNAME/PASSWORD.

# 4. Initialise the database
python init_project.py
```

Generate a random `SECRET_KEY`:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

## Running

```bash
uvicorn app:app --reload
```

Open http://127.0.0.1:8000/ in your browser.

- If you set `INITIAL_ADMIN_USERNAME` and `INITIAL_ADMIN_PASSWORD` in `.env` before first run, that account is created automatically.
- Otherwise, register an account at `/register` (select role `admin`).

## Training the recognition model

Place images under `dataset/criminals/<person_name>/` and `dataset/missing_persons/<person_name>/`, then:

```bash
python train_lbph.py
```

This writes `lbph_model.yml` and `label_map.npy`.

To run the standalone OpenCV window recogniser:

```bash
python live_recognition_haar.py
```

## Project layout

```
app.py                           # Uvicorn entrypoint (re-exports idvision.main:app)
init_project.py                  # One-off DB initialiser
train_lbph.py                    # CLI wrapper around idvision.training.train
live_recognition_haar.py         # Standalone OpenCV-window recogniser
liveness_mobilenet.py            # Blur-variance liveness check

idvision/                        # Main application package
    config.py                      # Env loading + constants
    db.py                          # SQLite schema + CRUD + auth
    recognition.py                 # LBPH FaceRecognizer + alert cooldown
    camera.py                      # Webcam + YuNet detector + gen_frames
    enrollment.py                  # Photo upload saving
    training.py                    # LBPH training + persons.json regen
    utils.py                       # Image validation + filename sanitising
    deps.py                        # Session helpers + template renderer
    main.py                        # FastAPI factory, wires everything together
    routes/
        auth.py                      # /, /login, /logout, /register
        dashboard.py                 # /dashboard, /video_feed, /retrain
        persons.py                   # /criminals/add, /missing/add

templates/                       # Jinja2 templates (_base, login, register,
                                 # dashboard, forbidden)
dataset/                         # Training images, grouped per person
dnn_model/                       # Caffe SSD face detector assets
face_detection_yunet_2023mar.onnx  # YuNet ONNX model (used by the live feed)
uploads/                         # Uploaded ID documents / photos
```

## Configuration

All runtime configuration lives in `.env` (see `.env.example`):

| Variable                  | Purpose                                             |
|---------------------------|-----------------------------------------------------|
| `SECRET_KEY`              | Session cookie signing key. **Required.**           |
| `INITIAL_ADMIN_USERNAME`  | Bootstraps first admin if no admin exists.          |
| `INITIAL_ADMIN_PASSWORD`  | Password for the bootstrap admin.                   |
| `DB_PATH`                 | SQLite file path. Defaults to `surveillance.db`.    |
| `CAMERA_INDEX`            | `cv2.VideoCapture` index. Defaults to `0`.          |

## Email alerts (optional)

When a known criminal or missing person is recognised in the live feed, IDVision
can send an email. Configure in `.env`:

```
EMAIL_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASSWORD=your-16-char-app-password
ALERT_EMAIL_TO=you@gmail.com,someone-else@example.com
```

For Gmail, generate an **App Password** (not your normal password) at
<https://myaccount.google.com/apppasswords>. 2-Step Verification must be on.

Delivery is asynchronous (background thread) so a slow SMTP server won't stall
the camera feed. Failures are logged and do not raise. Alerts are still written
to the SQLite DB and `alerts_log.txt` regardless of email config.

## Security notes

- `.env` and `surveillance.db` are gitignored. Never commit real credentials or production data.
- The default install uses `SessionMiddleware` — sessions are signed, not encrypted. Don't put sensitive data in the session.
- This project is educational. It is not hardened for production surveillance use.

## Status

Work in progress. See open items in project notes — recognition wiring, role-based route guards, upload validation, and UI polish are planned.
