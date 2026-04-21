from fastapi import Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")


def render(request: Request, name: str, status_code: int = 200, **ctx):
    return templates.TemplateResponse(request, name, ctx, status_code=status_code)


def current_user(request: Request):
    return request.session.get("user")


def redirect_login():
    return RedirectResponse("/", status_code=303)


def forbidden(request: Request, message: str = "Admin access required."):
    return render(request, "forbidden.html", status_code=403, message=message)
