from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from . import config, db
from .routes import include_all


def create_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(
        SessionMiddleware,
        secret_key=config.SECRET_KEY,
        max_age=config.SESSION_MAX_AGE_MINUTES * 60,
        same_site="lax",
        https_only=False,
    )
    db.init_db()
    include_all(app)
    return app


app = create_app()
