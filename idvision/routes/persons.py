from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import RedirectResponse

from .. import db
from ..deps import current_user, forbidden, redirect_login
from ..enrollment import save_uploads
from .dashboard import render_dashboard

router = APIRouter()


@router.post("/criminals/add")
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
        return redirect_login()
    if user.get("role") != "admin":
        return forbidden(request)

    name = name.strip()
    criminal_id = db.add_criminal(name, age, gender.strip(), crime_details.strip())
    image_path, err = save_uploads(photo, "criminals", criminal_id, name)
    if err:
        return render_dashboard(
            request, user,
            flash=f"Criminal added but photo rejected: {err}",
            flash_kind="err",
            status_code=400,
        )
    if image_path:
        db.update_criminal(criminal_id, image_path=image_path)
    return RedirectResponse("/dashboard", status_code=303)


@router.post("/missing/add")
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
        return redirect_login()
    if user.get("role") != "admin":
        return forbidden(request)

    name = name.strip()
    person_id = db.add_missing_person(name, age, gender.strip(), last_seen.strip())
    image_path, err = save_uploads(photo, "missing_persons", person_id, name)
    if err:
        return render_dashboard(
            request, user,
            flash=f"Person added but photo rejected: {err}",
            flash_kind="err",
            status_code=400,
        )
    if image_path:
        db.update_missing_person(person_id, image_path=image_path)
    return RedirectResponse("/dashboard", status_code=303)
