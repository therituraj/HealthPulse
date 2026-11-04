"""Application factory."""
import logging

from flask import Flask, render_template, request, session
from sqlalchemy.exc import SQLAlchemyError

from .config import API_DIR, Config
from .extensions import db, db_ready, init_db
from .routes import admin, auth, reports

log = logging.getLogger("healthpulse")


def create_app():
    app = Flask(__name__, template_folder=str(API_DIR / "templates"), static_folder=str(API_DIR / "static"))
    app.config.from_object(Config)
    if app.config["SECRET_KEY_IS_FALLBACK"]:
        log.warning("SECRET_KEY is not set: sessions will break between serverless instances. Set it in Vercel.")
    if not app.config["DB_PERSISTENT"]:
        log.warning("DATABASE_URL is not set: using a temporary SQLite database in /tmp.")

    db.init_app(app)
    init_db(app, force=True)  # never raises; the app boots even when the DB is down

    @app.before_request
    def _retry_db_if_needed():
        if not db_ready() and request.endpoint != "static":
            init_db(app)  # throttled to one attempt every few seconds

    @app.template_filter("iso_utc")
    def iso_utc(value):
        return value.isoformat() + "Z" if value else ""

    @app.template_filter("fmt_date")
    def fmt_date(value, with_time=False):
        if not value:
            return ""
        return value.strftime("%d %b %Y, %H:%M UTC" if with_time else "%d %b %Y")

    def _error(code, message):
        return render_template("error.html", code=code, message=message, user=session.get("user")), code

    @app.errorhandler(404)
    def not_found(_e):
        return _error(404, "We could not find that page.")

    @app.errorhandler(413)
    def too_large(_e):
        return _error(413, "That file is too large (4 MB maximum).")

    @app.errorhandler(SQLAlchemyError)
    def db_error(exc):
        db.session.rollback()
        log.exception("Database error: %s", exc)
        return _error(503, "The database is not reachable right now. Please try again in a moment.")

    auth.register(app)
    reports.register(app)
    admin.register(app)
    return app
