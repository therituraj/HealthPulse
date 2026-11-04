"""Login, registration, profile, password and file-upload routes."""
from io import BytesIO

from flask import abort, flash, redirect, render_template, request, send_file, session, url_for

from ..extensions import db
from ..models import UploadedFile, User, new_user_uuid
from .helpers import (current_user, is_valid_email, is_valid_name, is_valid_password, login_required,
                      require_db, route_enabled)

ALLOWED_UPLOADS = ("image/", "application/pdf")


def _session_payload(u):
    return {"id": u.id, "uuid": u.uuid, "name": u.name, "email": u.email, "role": u.role}


def register(app):
    @app.route("/error_404")
    def error_404():
        return render_template("error.html", code=404, message="That page is not available.", user=current_user()), 404

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            email = (request.form.get("email") or "").strip().lower()
            password = request.form.get("password") or ""
            if not email or not password:
                flash("All fields must be filled out.", "error")
            elif not is_valid_email(email):
                flash("Please enter a valid email address.", "error")
            elif require_db():
                user = User.query.filter_by(email=email).first()
                if user and user.check_password(password):
                    if user.role == "admin":
                        session.pop("user", None)
                        session["admin"] = _session_payload(user)
                        return redirect(url_for("admin_dashboard"))
                    session.pop("admin", None)
                    session["user"] = _session_payload(user)
                    return redirect(url_for("home"))
                flash("Invalid email or password. Please try again.", "error")
        return render_template("login.html")

    @app.route("/register", methods=["GET", "POST"])
    def register_user():
        if request.method == "POST":
            name = (request.form.get("name") or "").strip()
            email = (request.form.get("email") or "").strip().lower()
            password = request.form.get("password") or ""
            confirm = request.form.get("confirm_password") or ""
            if not name or not email or not password or not confirm:
                flash("All fields must be filled out.", "error")
            elif password != confirm:
                flash("Password and confirm password do not match.", "error")
            elif not is_valid_name(name):
                flash("Please enter a valid name.", "error")
            elif not is_valid_email(email):
                flash("Please enter a valid email address.", "error")
            elif not is_valid_password(password):
                flash("Please enter a strong password.", "error")
            elif not request.form.get("term_condition"):
                flash("Terms and conditions must be accepted.", "error")
            elif require_db():
                if User.query.filter_by(email=email).first():
                    flash("Email already registered. Please use a different email.", "error")
                else:
                    user = User(name=name, email=email, role="user")
                    user.set_password(password)  # only the hash is stored (no plain-text copy any more)
                    db.session.add(user)
                    db.session.commit()
                    flash("Signup successful! Please login.", "success")
                    return redirect(url_for("login"))
        return render_template("register.html")

    # The old template/endpoint name was `register`; keep url_for('register') working.
    app.add_url_rule("/register", endpoint="register", view_func=app.view_functions["register_user"],
                     methods=["GET", "POST"])

    @app.route("/logout")
    def logout():
        if session.get("user"):
            session.pop("user", None)
        else:
            session.pop("admin", None)
        flash("Logout successful!", "success")
        return redirect(url_for("login"))

    # ------------------------------------------------------------------ profile
    @app.route("/my_profile")
    @login_required
    @route_enabled("my_profile")
    def my_profile():
        user = current_user()
        profile = User.query.get(user["id"]) if require_db() else None
        return render_template("my_profile.html", user=user, profile_data=profile)

    @app.route("/edit_profile/<uuid>", methods=["GET", "POST"])
    @login_required
    def edit_profile(uuid):
        user = current_user()
        if user["uuid"] != uuid:
            return redirect(url_for("my_profile"))
        if not require_db():
            return redirect(url_for("my_profile"))
        profile = User.query.get_or_404(user["id"])
        if request.method == "POST":
            name = (request.form.get("name") or "").strip()
            email = (request.form.get("email") or "").strip().lower()
            if not is_valid_name(name):
                flash("Please enter a valid name.", "error")
            elif not is_valid_email(email):
                flash("Please enter a valid email address.", "error")
            elif User.query.filter(User.email == email, User.id != profile.id).first():
                flash("That email is already used by another account.", "error")
            else:
                profile.name, profile.email = name, email
                profile.dob = request.form.get("dob") or None
                profile.address = request.form.get("address") or None
                profile.mobile_no = request.form.get("mobile_no") or None
                db.session.commit()
                session["user"] = _session_payload(profile)
                flash("profile data changed successfully", "success")
                return redirect(url_for("my_profile"))
            return redirect(url_for("edit_profile", uuid=uuid))
        return render_template("edit_profile.html", profile_data=profile, user=user)

    @app.route("/change_password", methods=["GET", "POST"])
    @login_required
    def change_password():
        user = current_user()
        if request.method == "POST":
            current = request.form.get("current_password") or ""
            new = request.form.get("new_password") or ""
            retype = request.form.get("retype_new_password") or ""
            if not current or not new or not retype:
                flash("All fields must be filled out.", "error")
            elif not is_valid_password(new):
                flash("Please enter a strong password.", "error")
            elif new != retype:
                flash("New password and Retype new password must be same.", "error")
            elif require_db():
                account = User.query.get(user["id"])
                if account and account.check_password(current):
                    account.set_password(new)
                    db.session.commit()
                    flash("Password changed successfully", "success")
                else:
                    flash("Please enter correct current password.", "error")
            return redirect(url_for("change_password"))
        return render_template("change_password.html", user=user)

    # ------------------------------------------------------------------ uploads (was GridFS)
    @app.route("/upload_file")
    @login_required
    def upload_file():
        return render_template("upload_file.html", user=current_user())

    @app.route("/upload/<uuid>", methods=["POST"])
    @login_required
    def upload(uuid):
        user = current_user()
        file = request.files.get("file")
        if user["uuid"] != uuid:
            abort(403)
        if not file or not file.filename:
            flash("No file provided.", "error")
            return redirect(url_for("upload_file"))
        if not (file.mimetype or "").startswith(ALLOWED_UPLOADS):
            flash("Only images and PDF files can be uploaded.", "error")
            return redirect(url_for("upload_file"))
        if not require_db():
            return redirect(url_for("upload_file"))
        db.session.add(UploadedFile(user_id=user["id"], filename=file.filename[:255],
                                    content_type=file.mimetype, data=file.read()))
        db.session.commit()
        flash(f"File '{file.filename}' uploaded successfully!", "success")
        return redirect(url_for("my_profile"))

    @app.route("/fetch/<int:file_id>")
    @login_required
    def fetch(file_id):
        user = current_user()
        if not require_db():
            return redirect(url_for("my_profile"))
        f = UploadedFile.query.filter_by(id=file_id, user_id=user["id"]).first_or_404()
        return send_file(BytesIO(f.data), mimetype=f.content_type or "application/octet-stream",
                         as_attachment=True, download_name=f.filename)
