import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import cv2

from database import (
    init_db,
    register_user,
    authenticate_user,
    add_criminal,
    add_missing_person,
    get_criminals,
    get_missing_persons,
    get_alerts,
    get_recent_alerts,
    update_criminal,
    update_missing_person,
    has_any_admin,
)
from recognition import FaceRecognizer, log_alert, prepare_face
from utils import (
    ImageValidationError,
    person_folder,
    safe_filename,
    validate_image_bytes,
)

load_dotenv()

SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY is not set. Copy .env.example to .env and fill in a random value."
    )

CAMERA_INDEX = int(os.environ.get("CAMERA_INDEX", "0"))
SESSION_MAX_AGE_MINUTES = int(os.environ.get("SESSION_MAX_AGE_MINUTES", "60"))

DATASET_DIR = Path("dataset")
ALLOWED_ROLES = {"admin", "viewer"}

app = FastAPI()
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    max_age=SESSION_MAX_AGE_MINUTES * 60,
    same_site="lax",
    https_only=False,
)

templates = Jinja2Templates(directory="templates")


def render(request, name, status_code=200, **ctx):
    return templates.TemplateResponse(request, name, ctx, status_code=status_code)


init_db()

MODEL_PATH = "face_detection_yunet_2023mar.onnx"
camera = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)

face_detector = cv2.FaceDetectorYN.create(
    MODEL_PATH,
    "",
    (320, 320),
    0.9,
    0.3,
    5000
)

recognizer = FaceRecognizer()


def current_user(request: Request):
    return request.session.get("user")


def _redirect_login():
    return RedirectResponse("/", status_code=303)


def _forbidden(request: Request, message="Admin access required."):
    return render(request, "forbidden.html", status_code=403, message=message)


def _save_uploads(uploads, category_folder: str, person_id: int, person_name: str):
    """Validate and save uploaded images under dataset/{category_folder}/{id}_{name}/.
    Returns (first_saved_path_or_empty_string, error_message_or_none)."""
    valid = [u for u in uploads if u and u.filename]
    if not valid:
        return "", None

    target = DATASET_DIR / category_folder / person_folder(person_id, person_name)
    target.mkdir(parents=True, exist_ok=True)

    first_path = ""
    for idx, upload in enumerate(valid):
        data = upload.file.read()
        try:
            ext = validate_image_bytes(data, upload.filename)
        except ImageValidationError as e:
            return "", f"{upload.filename}: {e}"
        fname = f"{safe_filename(person_name)}_{person_id}_{idx}{ext}"
        path = target / fname
        path.write_bytes(data)
        if not first_path:
            first_path = str(path)
    return first_path, None


def gen_frames():
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

                x = max(0, x)
                y = max(0, y)
                bw = max(1, bw)
                bh = max(1, bh)

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
                cv2.putText(
                    frame,
                    label,
                    (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    color,
                    2
                )

        ret, buffer = cv2.imencode(".jpg", frame)
        frame_bytes = buffer.tobytes()

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
        )


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    if current_user(request):
        return RedirectResponse("/dashboard", status_code=303)
    return render(request, "login.html")


@app.post("/login")
def do_login(request: Request, username: str = Form(...), password: str = Form(...)):
    user = authenticate_user(username.strip(), password)
    if user:
        request.session["user"] = {"username": user["username"], "role": user["role"]}
        return RedirectResponse("/dashboard", status_code=303)
    return render(request, "login.html", status_code=401, error="Invalid username or password.")


@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    user = current_user(request)
    bootstrap = not has_any_admin()
    if not bootstrap:
        if not user:
            return _redirect_login()
        if user.get("role") != "admin":
            return _forbidden(request, "Only admins can register new users.")
    return render(request, "register.html", bootstrap=bootstrap)


@app.post("/register")
def do_register(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
):
    user = current_user(request)
    bootstrap = not has_any_admin()

    if bootstrap:
        role = "admin"
    else:
        if not user:
            return _redirect_login()
        if user.get("role") != "admin":
            return _forbidden(request, "Only admins can register new users.")
        if role not in ALLOWED_ROLES:
            return render(request, "register.html", status_code=400,
                          bootstrap=False, error="Invalid role.")

    username = username.strip()
    if not username or not password:
        return render(request, "register.html", status_code=400,
                      bootstrap=bootstrap, error="Username and password are required.")

    if not register_user(username, password, role):
        return render(request, "register.html", status_code=400,
                      bootstrap=bootstrap, error="Username already exists.")
    return RedirectResponse("/" if bootstrap else "/dashboard", status_code=303)


def _render_dashboard(request: Request, user, flash=None, flash_kind=None, status_code=200):
    return render(
        request, "dashboard.html", status_code=status_code,
        user=user,
        is_admin=user.get("role") == "admin",
        criminals=get_criminals(),
        missing_persons=get_missing_persons(),
        alerts=get_alerts(),
        recent=get_recent_alerts(10),
        recognizer_ready=recognizer.ready,
        flash=flash,
        flash_kind=flash_kind,
    )


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    user = current_user(request)
    if not user:
        return _redirect_login()
    return _render_dashboard(request, user)


@app.post("/criminals/add")
async def create_criminal(
    request: Request,
    name: str = Form(...),
    crime_details: str = Form(...),
    age: int = Form(None),
    gender: str = Form(""),
    photo: list[UploadFile] = File(default=[]),
):
    user = current_user(request)
    if not user:
        return _redirect_login()
    if user.get("role") != "admin":
        return _forbidden(request)

    name = name.strip()
    criminal_id = add_criminal(name, age, gender.strip(), crime_details.strip())
    image_path, err = _save_uploads(photo, "criminals", criminal_id, name)
    if err:
        return _render_dashboard(
            request, user,
            flash=f"Criminal added but photo rejected: {err}",
            flash_kind="err",
            status_code=400,
        )
    if image_path:
        update_criminal(criminal_id, image_path=image_path)

    return RedirectResponse("/dashboard", status_code=303)


@app.post("/missing/add")
async def create_missing_person(
    request: Request,
    name: str = Form(...),
    last_seen: str = Form(...),
    age: int = Form(None),
    gender: str = Form(""),
    photo: list[UploadFile] = File(default=[]),
):
    user = current_user(request)
    if not user:
        return _redirect_login()
    if user.get("role") != "admin":
        return _forbidden(request)

    name = name.strip()
    person_id = add_missing_person(name, age, gender.strip(), last_seen.strip())
    image_path, err = _save_uploads(photo, "missing_persons", person_id, name)
    if err:
        return _render_dashboard(
            request, user,
            flash=f"Person added but photo rejected: {err}",
            flash_kind="err",
            status_code=400,
        )
    if image_path:
        update_missing_person(person_id, image_path=image_path)

    return RedirectResponse("/dashboard", status_code=303)


@app.post("/retrain")
def retrain(request: Request):
    user = current_user(request)
    if not user:
        return _redirect_login()
    if user.get("role") != "admin":
        return _forbidden(request)

    from train_lbph import train
    try:
        train()
    except SystemExit as e:
        return _render_dashboard(request, user, flash=str(e), flash_kind="err", status_code=400)
    except Exception as e:
        return _render_dashboard(request, user, flash=f"Training failed: {e}", flash_kind="err", status_code=500)

    global recognizer
    recognizer = FaceRecognizer()
    return _render_dashboard(
        request, user,
        flash="Model retrained. Recognition " + ("enabled." if recognizer.ready else "still disabled — check logs."),
        flash_kind="ok" if recognizer.ready else "err",
    )


@app.get("/video_feed")
def video_feed(request: Request):
    if not current_user(request):
        return _redirect_login()
    return StreamingResponse(
        gen_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)
