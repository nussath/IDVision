from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from .. import db
from ..camera import gen_frames, reload_recognizer
from ..camera import recognizer as _recognizer_module_ref  # noqa: F401  (live-binding)
from ..deps import current_user, forbidden, redirect_login, render

router = APIRouter()


def render_dashboard(request, user, flash=None, flash_kind=None, status_code=200):
    from .. import camera  # late import so we read the live-reloaded recognizer
    return render(
        request, "dashboard.html", status_code=status_code,
        user=user,
        is_admin=user.get("role") == "admin",
        criminals=db.get_criminals(),
        missing_persons=db.get_missing_persons(),
        alerts=db.get_alerts(),
        recent=db.get_recent_alerts(10),
        recognizer_ready=camera.recognizer.ready,
        flash=flash,
        flash_kind=flash_kind,
    )


@router.get("/dashboard")
def dashboard(request: Request):
    user = current_user(request)
    if not user:
        return redirect_login()
    return render_dashboard(request, user)


@router.get("/video_feed")
def video_feed(request: Request):
    if not current_user(request):
        return redirect_login()
    return StreamingResponse(
        gen_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@router.post("/retrain")
def retrain(request: Request):
    user = current_user(request)
    if not user:
        return redirect_login()
    if user.get("role") != "admin":
        return forbidden(request)

    from ..training import train
    try:
        train()
    except SystemExit as e:
        return render_dashboard(request, user, flash=str(e), flash_kind="err", status_code=400)
    except Exception as e:
        return render_dashboard(request, user, flash=f"Training failed: {e}", flash_kind="err", status_code=500)

    rec = reload_recognizer()
    return render_dashboard(
        request, user,
        flash="Model retrained. Recognition " + ("enabled." if rec.ready else "still disabled — check logs."),
        flash_kind="ok" if rec.ready else "err",
    )
