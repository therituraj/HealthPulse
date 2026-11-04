"""Database handle + resilient initialisation (the app must never crash because the DB is down)."""
import logging
import time

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
log = logging.getLogger("healthpulse")

_state = {"ready": False, "last_try": 0.0}
RETRY_SECONDS = 15


def db_ready() -> bool:
    return _state["ready"]


def init_db(app, force: bool = False) -> bool:
    """Create tables (and the optional admin). Safe to call repeatedly; failures are logged, never raised."""
    if _state["ready"]:
        return True
    now = time.time()
    if not force and now - _state["last_try"] < RETRY_SECONDS:
        return False
    _state["last_try"] = now
    try:
        from . import models  # noqa: F401  (registers the tables)

        with app.app_context():
            db.create_all()
            _seed_admin(app)
        _state["ready"] = True
        log.info("Database ready")
    except Exception as exc:  # noqa: BLE001 - any driver/network error must be survivable
        _state["ready"] = False
        log.warning("Database not available: %s", exc)
        try:
            with app.app_context():
                db.session.rollback()
        except Exception:  # noqa: BLE001
            pass
    return _state["ready"]


def _seed_admin(app):
    from .models import User

    email, password = app.config["ADMIN_EMAIL"], app.config["ADMIN_PASSWORD"]
    if not email or not password:
        return
    if User.query.filter_by(email=email).first():
        return
    admin = User(name="Administrator", email=email, role="admin")
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()
