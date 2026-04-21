import os

from dotenv import load_dotenv
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
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
)
from recognition import FaceRecognizer, log_alert, prepare_face

load_dotenv()

SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY is not set. Copy .env.example to .env and fill in a random value."
    )

CAMERA_INDEX = int(os.environ.get("CAMERA_INDEX", "0"))

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

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

def is_logged_in(request: Request):
    return request.session.get("user")

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
    user = request.session.get("user")
    if user:
        return RedirectResponse("/dashboard", status_code=303)

    return """
    <html>
    <head><title>Police Surveillance Login</title></head>
    <body style="font-family:Arial;padding:40px">
        <h2>Police Surveillance System</h2>
        <h3>Login</h3>
        <form method="post" action="/login">
            <input name="username" placeholder="Username" required><br><br>
            <input name="password" type="password" placeholder="Password" required><br><br>
            <button type="submit">Login</button>
        </form>
        <br>
        <a href="/register">Register New User</a>
    </body>
    </html>
    """

@app.get("/register", response_class=HTMLResponse)
def register_page():
    return """
    <html>
    <head><title>Register</title></head>
    <body style="font-family:Arial;padding:40px">
        <h2>Register User</h2>
        <form method="post" action="/register">
            <input name="username" placeholder="Username" required><br><br>
            <input name="password" type="password" placeholder="Password" required><br><br>
            <select name="role">
                <option value="viewer">Viewer</option>
                <option value="admin">Admin</option>
            </select><br><br>
            <button type="submit">Register</button>
        </form>
        <br>
        <a href="/">Back to Login</a>
    </body>
    </html>
    """

@app.post("/register")
def do_register(username: str = Form(...), password: str = Form(...), role: str = Form(...)):
    ok = register_user(username, password, role)
    if ok:
        return RedirectResponse("/", status_code=303)
    return HTMLResponse("<h3>Username already exists</h3><a href='/register'>Try again</a>", status_code=400)

@app.post("/login")
def do_login(request: Request, username: str = Form(...), password: str = Form(...)):
    user = authenticate_user(username, password)
    if user:
        request.session["user"] = {"username": user["username"], "role": user["role"]}
        return RedirectResponse("/dashboard", status_code=303)
    return HTMLResponse("<h3>Invalid username or password</h3><a href='/'>Back</a>", status_code=401)

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    user = is_logged_in(request)
    if not user:
        return RedirectResponse("/", status_code=303)

    criminals = get_criminals()
    missing_persons = get_missing_persons()
    alerts = get_alerts()

    criminal_rows = "".join(
        f"<tr><td>{c['id']}</td><td>{c['name']}</td><td>{c['crime_details']}</td><td>{c['status']}</td></tr>"
        for c in criminals
    ) or "<tr><td colspan='4'>No criminals added</td></tr>"

    missing_rows = "".join(
        f"<tr><td>{m['id']}</td><td>{m['name']}</td><td>{m['last_seen']}</td><td>{m['status']}</td></tr>"
        for m in missing_persons
    ) or "<tr><td colspan='4'>No missing persons added</td></tr>"

    alert_rows = "".join(
        f"<tr><td>{a['person_name']}</td><td>{a['category']}</td><td>{a['timestamp']}</td></tr>"
        for a in alerts
    ) or "<tr><td colspan='3'>No alerts</td></tr>"

    return f"""
    <html>
    <head><title>Dashboard</title></head>
    <body style="font-family:Arial;padding:30px">
        <h2>Welcome, {user['username']}</h2>
        <a href="/logout">Logout</a>

        <hr>
        <h3>Live Webcam Feed</h3>
        <img src="/video_feed" width="720" style="border:2px solid black;"><br><br>

        <hr>
        <h3>Add Criminal</h3>
        <form method="post" action="/criminals/add">
            <input name="name" placeholder="Name" required>
            <input name="age" type="number" placeholder="Age">
            <input name="gender" placeholder="Gender">
            <input name="crime_details" placeholder="Crime details" required>
            <button type="submit">Add Criminal</button>
        </form>

        <h3>Add Missing Person</h3>
        <form method="post" action="/missing/add">
            <input name="name" placeholder="Name" required>
            <input name="age" type="number" placeholder="Age">
            <input name="gender" placeholder="Gender">
            <input name="last_seen" placeholder="Last seen location" required>
            <button type="submit">Add Missing Person</button>
        </form>

        <hr>
        <h3>Criminals</h3>
        <table border="1" cellpadding="8">
            <tr><th>ID</th><th>Name</th><th>Crime</th><th>Status</th></tr>
            {criminal_rows}
        </table>

        <h3>Missing Persons</h3>
        <table border="1" cellpadding="8">
            <tr><th>ID</th><th>Name</th><th>Last Seen</th><th>Status</th></tr>
            {missing_rows}
        </table>

        <h3>Alerts</h3>
        <table border="1" cellpadding="8">
            <tr><th>Name</th><th>Category</th><th>Timestamp</th></tr>
            {alert_rows}
        </table>
    </body>
    </html>
    """

@app.post("/criminals/add")
def create_criminal(
    request: Request,
    name: str = Form(...),
    age: int = Form(None),
    gender: str = Form(""),
    crime_details: str = Form(...)
):
    if not is_logged_in(request):
        return RedirectResponse("/", status_code=303)

    add_criminal(name, age, gender, crime_details)
    return RedirectResponse("/dashboard", status_code=303)

@app.post("/missing/add")
def create_missing_person(
    request: Request,
    name: str = Form(...),
    age: int = Form(None),
    gender: str = Form(""),
    last_seen: str = Form(...)
):
    if not is_logged_in(request):
        return RedirectResponse("/", status_code=303)

    add_missing_person(name, age, gender, last_seen)
    return RedirectResponse("/dashboard", status_code=303)

@app.get("/video_feed")
def video_feed(request: Request):
    if not is_logged_in(request):
        return RedirectResponse("/", status_code=303)

    return StreamingResponse(
        gen_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)