"""SQLAlchemy models."""
import secrets
from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)  # stored as naive UTC


def new_user_uuid():
    return secrets.token_hex(4)  # 8 hex chars, same style as before


def new_public_id():
    return secrets.token_hex(6)  # 12 hex chars, used in report URLs


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(16), unique=True, index=True, nullable=False, default=new_user_uuid)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, index=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="user")
    dob = db.Column(db.String(20))
    address = db.Column(db.String(255))
    mobile_no = db.Column(db.String(30))
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    reports = db.relationship("Report", backref="owner", cascade="all, delete-orphan", lazy="dynamic")
    files = db.relationship("UploadedFile", backref="owner", cascade="all, delete-orphan", lazy="dynamic")

    def set_password(self, raw):
        self.password_hash = generate_password_hash(raw, method="pbkdf2:sha256")

    def check_password(self, raw):
        return check_password_hash(self.password_hash, raw)

    # ---- compatibility helpers so older Mongo-style templates keep working ----
    @property
    def _id(self):
        return self.id

    @property
    def created_At(self):
        return self.created_at

    @property
    def image_files(self):
        return [{"file_id": f.id, "filename": f.filename} for f in self.files.order_by(UploadedFile.id.desc())]

    def get(self, key, default=None):
        return getattr(self, key, default)


class Report(db.Model):
    __tablename__ = "reports"

    TITLES = {"diabetes": "Diabetes Risk Report", "heart": "Heart Disease Risk Report"}

    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(16), unique=True, index=True, nullable=False, default=new_public_id)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    kind = db.Column(db.String(20), nullable=False, index=True)  # "diabetes" | "heart"
    inputs = db.Column(db.JSON, nullable=False, default=dict)  # validated form values
    prediction = db.Column(db.Integer, nullable=False)  # 0 / 1
    probability = db.Column(db.Float)  # model's P(class 1) if available
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)

    @property
    def title(self):
        return self.TITLES.get(self.kind, "Health Report")

    @property
    def is_high_risk(self):
        return self.prediction == 1

    @property
    def risk_label(self):
        return "Higher risk" if self.is_high_risk else "Lower risk"

    @property
    def percent(self):
        return None if self.probability is None else round(self.probability * 100, 1)


class GlobalSetting(db.Model):
    """Admin switch per route. No row (or DB down) means the route is enabled."""

    __tablename__ = "global_settings"

    id = db.Column(db.Integer, primary_key=True)
    route_name = db.Column(db.String(80), unique=True, nullable=False)
    is_enabled = db.Column(db.Boolean, nullable=False, default=True)


class UploadedFile(db.Model):
    """Replaces GridFS: small files kept in the database."""

    __tablename__ = "uploaded_files"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    content_type = db.Column(db.String(100))
    data = db.Column(db.LargeBinary, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
