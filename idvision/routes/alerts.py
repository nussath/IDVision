from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

from .. import config, db
from ..deps import current_user, redirect_login, render

router = APIRouter()


@router.get("/alerts")
def alerts_page(request: Request):
    user = current_user(request)
    if not user:
        return redirect_login()
    return render(request, "alerts.html",
                  user=user,
                  is_admin=user.get("role") == "admin",
                  alerts=db.get_alerts(),
                  active="alerts")


@router.get("/snapshot/{name}")
def snapshot(request: Request, name: str):
    if not current_user(request):
        return redirect_login()
    # Defence against path traversal: only serve files that live directly
    # under SNAPSHOT_DIR, reject anything that resolves outside it.
    safe_name = Path(name).name
    path = (config.SNAPSHOT_DIR / safe_name).resolve()
    root = config.SNAPSHOT_DIR.resolve()
    try:
        path.relative_to(root)
    except ValueError:
        return redirect_login()
    if not path.is_file():
        return redirect_login()
    return FileResponse(path)
