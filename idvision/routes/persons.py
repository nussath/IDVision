from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import RedirectResponse

from .. import db
from ..deps import current_user, forbidden, redirect_login, render
from ..enrollment import remove_person_folder, save_uploads

router = APIRouter()


def _person_page(request, active, flash=None, flash_kind=None, status_code=200):
    user = current_user(request)
    ctx = {
        "user": user,
        "is_admin": user and user.get("role") == "admin",
        "active": active,
        "flash": flash,
        "flash_kind": flash_kind,
        "criminals": db.get_criminals(),
        "missing_persons": db.get_missing_persons(),
    }
    template = "criminals.html" if active == "criminals" else "missing.html"
    return render(request, template, status_code=status_code, **ctx)


@router.get("/criminals")
def criminals_page(request: Request):
    if not current_user(request):
        return redirect_login()
    return _person_page(request, "criminals")


@router.get("/missing")
def missing_page(request: Request):
    if not current_user(request):
        return redirect_login()
    return _person_page(request, "missing")


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
        return _person_page(request, "criminals",
                            flash=f"Criminal added but photo rejected: {err}",
                            flash_kind="err", status_code=400)
    if image_path:
        db.update_criminal(criminal_id, image_path=image_path)
    return RedirectResponse("/criminals", status_code=303)


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
        return _person_page(request, "missing",
                            flash=f"Person added but photo rejected: {err}",
                            flash_kind="err", status_code=400)
    if image_path:
        db.update_missing_person(person_id, image_path=image_path)
    return RedirectResponse("/missing", status_code=303)


@router.post("/criminals/{criminal_id}/delete")
def delete_criminal_route(request: Request, criminal_id: int):
    user = current_user(request)
    if not user:
        return redirect_login()
    if user.get("role") != "admin":
        return forbidden(request)

    row = db.get_criminal(criminal_id)
    if not row:
        return _person_page(request, "criminals",
                            flash="Criminal not found.",
                            flash_kind="err", status_code=404)
    db.delete_criminal(criminal_id)
    removed = remove_person_folder("criminals", criminal_id, row["name"])
    msg = f"Deleted criminal '{row['name']}'."
    if removed:
        msg += " Dataset folder removed — click Retrain on the Admin page."
    return _person_page(request, "criminals", flash=msg, flash_kind="ok")


@router.post("/missing/{person_id}/delete")
def delete_missing_route(request: Request, person_id: int):
    user = current_user(request)
    if not user:
        return redirect_login()
    if user.get("role") != "admin":
        return forbidden(request)

    row = db.get_missing_person(person_id)
    if not row:
        return _person_page(request, "missing",
                            flash="Missing person not found.",
                            flash_kind="err", status_code=404)
    db.delete_missing_person(person_id)
    removed = remove_person_folder("missing_persons", person_id, row["name"])
    msg = f"Deleted missing person '{row['name']}'."
    if removed:
        msg += " Dataset folder removed — click Retrain on the Admin page."
    return _person_page(request, "missing", flash=msg, flash_kind="ok")
