"""Decorators and small helpers shared by all routes."""
import logging
import re
from functools import wraps

from flask import abort, current_app, flash, redirect, session, url_for
from sqlalchemy.exc import SQLAlchemyError

from ..extensions import db, db_ready, init_db

log = logging.getLogger("healthpulse")

_EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
_PASSWORD = re.compile(r"^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$")


def is_valid_name(name):
    return bool(name) and len(name.strip()) >= 3


def is_valid_email(email):
    return bool(email) and bool(_EMAIL.fullmatch(email))


def is_valid_password(password):
    return bool(password) and bool(_PASSWORD.match(password))


def current_user():
    """The logged-in normal user (dict from the session) or None. Old sessions without an id are ignored."""
    user = session.get("user")
    return user if user and user.get("id") else None


def require_db():
    """True when the database can be used; otherwise flashes a friendly message and returns False."""
    if db_ready() or init_db(current_app):
        return True
    flash("The database is not reachable right now. Please try again in a moment.", "error")
    return False


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        user = current_user()
        if user and user.get("role") == "user":
            return view(*args, **kwargs)
        session.pop("user", None)
        flash("You must be logged in to access this page.", "error")
        return redirect(url_for("login"))

    return wrapper


def only_admin(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        admin = session.get("admin")
        if admin and admin.get("role") == "admin":
            return view(*args, **kwargs)
        return redirect(url_for("login"))

    return wrapper


def is_route_enabled(route_name):
    """Enabled unless an admin explicitly switched it off. DB down / no row / any error => enabled."""
    if not db_ready():
        return True
    try:
        from ..models import GlobalSetting

        setting = GlobalSetting.query.filter_by(route_name=route_name).first()
        return True if setting is None else bool(setting.is_enabled)
    except SQLAlchemyError:
        db.session.rollback()
        return True
    except Exception:  # noqa: BLE001
        return True


def route_enabled(route_name):
    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            if not is_route_enabled(route_name):
                abort(404)
            return view(*args, **kwargs)

        return wrapper

    return decorator
