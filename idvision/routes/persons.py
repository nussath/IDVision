from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import RedirectResponse

from .. import db
from ..deps import current_user, forbidden, redirect_login
from ..enrollment import remove_person_folder, save_uploads
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


@router.post("/criminals/{criminal_id}/delete")
def delete_criminal_route(request: Request, criminal_id: int):
    user = current_user(request)
    if not user:
        return redirect_login()
    if user.get("role") != "admin":
        return forbidden(request)

    row = db.get_criminal(criminal_id)
    if not row:
        return render_dashboard(request, user, flash="Criminal not found.",
                                flash_kind="err", status_code=404)

    db.delete_criminal(criminal_id)
    removed = remove_person_folder("criminals", criminal_id, row["name"])
    msg = f"Deleted criminal '{row['name']}'."
    if removed:
        msg += " Dataset folder removed — click Retrain to update the model."
    return render_dashboard(request, user, flash=msg, flash_kind="ok")


@router.post("/missing/{person_id}/delete")
def delete_missing_route(request: Request, person_id: int):
    user = current_user(request)
    if not user:
        return redirect_login()
    if user.get("role") != "admin":
        return forbidden(request)

    row = db.get_missing_person(person_id)
    if not row:
        return render_dashboard(request, user, flash="Missing person not found.",
                                flash_kind="err", status_code=404)

    db.delete_missing_person(person_id)
    removed = remove_person_folder("missing_persons", person_id, row["name"])
    msg = f"Deleted missing person '{row['name']}'."
    if removed:
        msg += " Dataset folder removed — click Retrain to update the model."
    return render_dashboard(request, user, flash=msg, flash_kind="ok")
