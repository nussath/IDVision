from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from .. import config, db
from ..deps import current_user, forbidden, redirect_login, render

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    if current_user(request):
        return RedirectResponse("/dashboard", status_code=303)
    return render(request, "login.html")


@router.post("/login")
def do_login(request: Request, username: str = Form(...), password: str = Form(...)):
    user = db.authenticate_user(username.strip(), password)
    if user:
        request.session["user"] = {"username": user["username"], "role": user["role"]}
        return RedirectResponse("/dashboard", status_code=303)
    return render(request, "login.html", status_code=401, error="Invalid username or password.")


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    user = current_user(request)
    bootstrap = not db.has_any_admin()
    if not bootstrap:
        if not user:
            return redirect_login()
        if user.get("role") != "admin":
            return forbidden(request, "Only admins can register new users.")
    return render(request, "register.html", bootstrap=bootstrap)


@router.post("/register")
def do_register(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
):
    user = current_user(request)
    bootstrap = not db.has_any_admin()

    if bootstrap:
        role = "admin"
    else:
        if not user:
            return redirect_login()
        if user.get("role") != "admin":
            return forbidden(request, "Only admins can register new users.")
        if role not in config.ALLOWED_ROLES:
            return render(request, "register.html", status_code=400,
                          bootstrap=False, error="Invalid role.")

    username = username.strip()
    if not username or not password:
        return render(request, "register.html", status_code=400,
                      bootstrap=bootstrap, error="Username and password are required.")

    if not db.register_user(username, password, role):
        return render(request, "register.html", status_code=400,
                      bootstrap=bootstrap, error="Username already exists.")
    return RedirectResponse("/" if bootstrap else "/dashboard", status_code=303)


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)
