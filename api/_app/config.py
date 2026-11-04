"""All configuration comes from environment variables (.env locally, Vercel dashboard in production)."""
import os
import secrets
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

API_DIR = Path(__file__).resolve().parent.parent
load_dotenv(find_dotenv(usecwd=True))
load_dotenv(API_DIR.parent / ".env")

IS_VERCEL = bool(os.getenv("VERCEL"))


def _database_url() -> str:
    url = (os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL") or "").strip()
    if url.startswith("postgres://"):  # SQLAlchemy needs "postgresql://"
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("mongodb"):  # old MONGO_URI style values are not usable with SQLAlchemy
        url = ""
    return url


_DB_URL = _database_url()


def _engine_options(url: str) -> dict:
    if url.startswith("sqlite"):
        return {}
    opts = {"pool_pre_ping": True, "pool_recycle": 280, "pool_size": 2, "max_overflow": 3}
    if url.startswith("postgresql"):
        opts["connect_args"] = {"connect_timeout": 5}  # fail fast instead of hanging a serverless call
    return opts


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_hex(32)
    SECRET_KEY_IS_FALLBACK = not os.getenv("SECRET_KEY")

    # If no DATABASE_URL is set the app still boots, using a temporary SQLite file
    # (Vercel only allows writing to /tmp, and it is wiped between cold starts).
    DB_PERSISTENT = bool(_DB_URL)
    SQLALCHEMY_DATABASE_URI = _DB_URL or "sqlite:////tmp/healthpulse.db"
    SQLALCHEMY_ENGINE_OPTIONS = _engine_options(_DB_URL or "sqlite")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    MAX_CONTENT_LENGTH = 4 * 1024 * 1024  # Vercel rejects bodies > 4.5 MB anyway
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = IS_VERCEL

    # ML models
    MODEL_DIR = Path(os.getenv("MODEL_DIR") or API_DIR / "data")
    DIABETES_MODEL_FILE = os.getenv("DIABETES_MODEL_FILE", "Diabetes_Prediction_Random_Forest_Model.pkl")
    HEART_MODEL_FILE = os.getenv("HEART_MODEL_FILE", "Heart_Disease_Prediction_Model.pkl")
    # The Kaggle "cardio" dataset stores age in DAYS. Set true if your model was trained that way.
    HEART_AGE_IN_DAYS = os.getenv("HEART_AGE_IN_DAYS", "false").lower() in ("1", "true", "yes")

    ADMIN_EMAIL = (os.getenv("ADMIN_EMAIL") or "").strip().lower()
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD") or ""
