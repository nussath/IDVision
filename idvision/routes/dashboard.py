from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, StreamingResponse

from .. import db
from ..camera import gen_frames, is_stopped, start_camera, stop_camera
from ..deps import current_user, redirect_login, render

router = APIRouter()


def _base_context(request, active, **extra):
    user = current_user(request)
    ctx = {
        "user": user,
        "is_admin": user and user.get("role") == "admin",
        "active": active,
    }
    ctx.update(extra)
    return ctx


@router.get("/dashboard")
def dashboard(request: Request):
    user = current_user(request)
    if not user:
        return redirect_login()
    from ..camera import recognizer
    recent = db.get_recent_alerts(10)
    criminals = db.get_criminals()
    missing = db.get_missing_persons()
    stats = {
        "criminals": len(criminals),
        "missing": len(missing),
        "alerts": len(db.get_alerts()),
    }
    return render(request, "dashboard.html",
                  **_base_context(request, "dashboard",
                                  stats=stats,
                                  recent=recent,
                                  recognizer_ready=recognizer.ready))


@router.get("/camera")
def camera_page(request: Request):
    if not current_user(request):
        return redirect_login()
    from ..camera import recognizer
    return render(request, "camera.html",
                  **_base_context(request, "camera",
                                  recognizer_ready=recognizer.ready,
                                  camera_stopped=is_stopped()))


@router.get("/video_feed")
def video_feed(request: Request):
    if not current_user(request):
        return redirect_login()
    return StreamingResponse(
        gen_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@router.post("/camera/stop")
def camera_stop(request: Request):
    if not current_user(request):
        return redirect_login()
    stop_camera()
    return RedirectResponse("/camera", status_code=303)


@router.post("/camera/start")
def camera_start(request: Request):
    if not current_user(request):
        return redirect_login()
    start_camera()
    return RedirectResponse("/camera", status_code=303)
