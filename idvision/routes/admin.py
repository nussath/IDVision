from fastapi import APIRouter, Request

from .. import notifications
from ..camera import reload_recognizer
from ..deps import current_user, forbidden, redirect_login, render


router = APIRouter()


def _admin_context(request, flash=None, flash_kind=None):
    return {
        "user": current_user(request),
        "is_admin": True,
        "active": "admin",
        "flash": flash,
        "flash_kind": flash_kind,
        "email_problems": notifications.configuration_status(),
        "email_recipients": notifications.ALERT_EMAIL_TO,
    }


@router.get("/admin")
def admin_page(request: Request):
    user = current_user(request)
    if not user:
        return redirect_login()
    if user.get("role") != "admin":
        return forbidden(request)
    return render(request, "admin.html", **_admin_context(request))


@router.post("/admin/test-email")
def test_email(request: Request):
    user = current_user(request)
    if not user:
        return redirect_login()
    if user.get("role") != "admin":
        return forbidden(request)

    ok, msg = notifications.send_test_email()
    return render(request, "admin.html",
                  **_admin_context(request, flash=msg, flash_kind="ok" if ok else "err"))


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
        return render(request, "admin.html",
                      **_admin_context(request, flash=str(e), flash_kind="err"))
    except Exception as e:
        return render(request, "admin.html",
                      **_admin_context(request, flash=f"Training failed: {e}", flash_kind="err"))

    rec = reload_recognizer()
    suffix = "enabled." if rec.ready else "still disabled — check logs."
    return render(request, "admin.html",
                  **_admin_context(request,
                                   flash=f"Model retrained. Recognition {suffix}",
                                   flash_kind="ok" if rec.ready else "err"))
