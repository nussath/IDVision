from . import auth, dashboard, persons


def include_all(app):
    app.include_router(auth.router)
    app.include_router(dashboard.router)
    app.include_router(persons.router)
