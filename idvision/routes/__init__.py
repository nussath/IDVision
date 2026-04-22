from . import admin, alerts, auth, dashboard, persons


def include_all(app):
    app.include_router(auth.router)
    app.include_router(dashboard.router)
    app.include_router(persons.router)
    app.include_router(alerts.router)
    app.include_router(admin.router)
