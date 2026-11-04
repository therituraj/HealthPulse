"""Admin area (dashboard, users, route switches, database viewer)."""
from datetime import datetime

from flask import flash, jsonify, redirect, render_template, request, session, url_for
from sqlalchemy.exc import SQLAlchemyError

from ..extensions import db, db_ready
from ..models import GlobalSetting, Report, UploadedFile, User
from .helpers import is_valid_email, is_valid_name, is_valid_password, only_admin, require_db

TABLES = {"users": User, "reports": Report, "global_settings": GlobalSetting, "uploaded_files": UploadedFile}
HIDDEN_COLUMNS = {"password_hash", "data"}


def register(app):
    def admin():
        return session.get("admin")

    @app.route("/admin/dashboard", methods=["GET", "POST"])
    @only_admin
    def admin_dashboard():
        total_user = total_reports = 0
        if db_ready():
            try:
                total_user, total_reports = User.query.count(), Report.query.count()
            except SQLAlchemyError:
                db.session.rollback()
        return render_template("admin/dashboard.html", admin=admin(), total_user=total_user,
                               total_reports=total_reports, db_ready=db_ready(),
                               db_persistent=app.config["DB_PERSISTENT"])

    @app.route("/admin/user_detail", methods=["GET", "POST"])
    @only_admin
    def user_detail():
        data = User.query.order_by(User.id).all() if require_db() else []
        return render_template("admin/user_detail.html", admin=admin(), user_data=data)

    @app.route("/admin/settings", methods=["GET", "POST"])
    @only_admin
    def settings():
        data = GlobalSetting.query.order_by(GlobalSetting.route_name).all() if require_db() else []
        return render_template("admin/settings.html", admin=admin(), global_data=data)

    @app.route("/enable_route/<route_name>", methods=["POST"])
    @only_admin
    def enable_route(route_name):
        if require_db():
            setting = GlobalSetting.query.filter_by(route_name=route_name).first()
            if setting:
                setting.is_enabled = bool(request.form.get("enableCheckbox"))
                db.session.commit()
                flash(f"{route_name} changed successfully", "success")
        return redirect(url_for("settings"))

    @app.route("/view_user/<int:user_id>")
    @only_admin
    def view_user(user_id):
        user = User.query.get(user_id) if require_db() else None
        if not user:
            flash("some problem in loading this page please try again", "error")
            return redirect(url_for("user_detail"))
        return render_template("admin/view_user.html", users=user, admin=admin())

    @app.route("/add_user", methods=["GET", "POST"])
    @only_admin
    def add_user():
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
            elif require_db():
                if User.query.filter_by(email=email).first():
                    flash("Email already registered. Please use a different email.", "error")
                else:
                    user = User(name=name, email=email, role="user")
                    user.set_password(password)
                    db.session.add(user)
                    db.session.commit()
                    flash("User added successfully.", "success")
                    return redirect(url_for("user_detail"))
            return redirect(url_for("add_user"))
        return render_template("admin/add_user.html", admin=admin())

    @app.route("/edit_user/<int:user_id>", methods=["GET", "POST"])
    @only_admin
    def edit_user(user_id):
        if not require_db():
            return redirect(url_for("user_detail"))
        user = User.query.get(user_id)
        if not user:
            flash("Some problem in loading user.please try again", "error")
            return redirect(url_for("user_detail"))
        if request.method == "POST":
            name = (request.form.get("name") or "").strip()
            email = (request.form.get("email") or "").strip().lower()
            if not is_valid_name(name):
                flash("Please enter a valid name.", "error")
            elif not is_valid_email(email):
                flash("Please enter a valid email address.", "error")
            elif User.query.filter(User.email == email, User.id != user.id).first():
                flash("That email is already used by another account.", "error")
            else:
                user.name, user.email = name, email
                user.dob = request.form.get("dob") or None
                user.address = request.form.get("address") or None
                user.mobile_no = request.form.get("mobile_no") or None
                db.session.commit()
                flash("Data changed successfully", "success")
                return redirect(url_for("user_detail"))
            return redirect(url_for("edit_user", user_id=user_id))
        return render_template("admin/edit_user.html", users=user, admin=admin())

    @app.route("/change_password/<int:user_id>", methods=["GET", "POST"])
    @only_admin
    def change_password_user(user_id):
        if not require_db():
            return redirect(url_for("user_detail"))
        user = User.query.get(user_id)
        if not user:
            flash("Some problem in loading the page.", "error")
            return redirect(url_for("user_detail"))
        if request.method == "POST":
            password = request.form.get("password") or ""
            if not is_valid_password(password):
                flash("Please enter a strong password.", "error")
            else:  # an admin can reset a password without knowing the old one
                user.set_password(password)
                db.session.commit()
                flash("Password changed successfully", "success")
                return redirect(url_for("user_detail"))
            return redirect(url_for("change_password_user", user_id=user_id))
        return render_template("admin/change_password_user.html", users=user, admin=admin())

    @app.route("/delete_user/<int:user_id>", methods=["GET", "POST"])
    @only_admin
    def delete_user(user_id):
        if not require_db():
            return redirect(url_for("user_detail"))
        user = User.query.get(user_id)
        if not user:
            flash("Some problem in loading the page.", "error")
            return redirect(url_for("user_detail"))
        if request.method == "POST":
            db.session.delete(user)  # reports and files are removed with the user
            db.session.commit()
            flash(f"User with id {user_id} deleted successfully.", "success")
            return redirect(url_for("user_detail"))
        return render_template("admin/delete_user.html", users=user, admin=admin())

    # ------------------------------------------------------------------ route switches
    @app.route("/admin/add_route", methods=["GET", "POST"])
    @only_admin
    def add_route():
        if request.method == "POST":
            route_name = (request.form.get("route_name") or "").strip()
            status = request.form.get("status")
            if not route_name or not status:
                flash("All fields must be filled out.", "error")
            elif require_db():
                if GlobalSetting.query.filter_by(route_name=route_name).first():
                    flash(f"{route_name} already registered. Please use a different route_name.", "error")
                else:
                    db.session.add(GlobalSetting(route_name=route_name, is_enabled=(status == "True")))
                    db.session.commit()
                    flash("Route Added successful.", "success")
                    return redirect(url_for("settings"))
            return redirect(url_for("add_route"))
        return render_template("admin/add_route.html", admin=admin())

    @app.route("/admin/update_route", methods=["GET", "POST"])
    @only_admin
    def update_route():
        if request.method == "POST":
            select_route = request.form.get("select_route")
            route_name = (request.form.get("route_name") or "").strip()
            if not route_name:
                flash("Please enter the new route name.", "error")
            elif require_db():
                setting = GlobalSetting.query.filter_by(route_name=select_route).first()
                if setting:
                    setting.route_name = route_name
                    db.session.commit()
                    flash("Route changed successfully", "success")
                    return redirect(url_for("settings"))
                flash("Route not found.", "error")
            return redirect(url_for("update_route"))
        data = GlobalSetting.query.all() if require_db() else []
        return render_template("admin/update_route.html", admin=admin(), global_data=data)

    @app.route("/admin/delete_route", methods=["GET", "POST"])
    @only_admin
    def delete_route():
        if request.method == "POST":
            select_route = request.form.get("select_route")
            if not select_route:
                flash("please select route to delete.", "error")
            elif require_db():
                setting = GlobalSetting.query.filter_by(route_name=select_route).first()
                if setting:
                    db.session.delete(setting)
                    db.session.commit()
                    flash("Route Deleted successfully", "success")
                    return redirect(url_for("settings"))
                flash("Route Does not deleted", "error")
            return redirect(url_for("delete_route"))
        data = GlobalSetting.query.all() if require_db() else []
        return render_template("admin/delete_route.html", admin=admin(), global_data=data)

    # ------------------------------------------------------------------ database viewer
    @app.route("/admin/database")
    @only_admin
    def database():
        return render_template("admin/database.html", collection_names=list(TABLES), admin=admin())

    @app.route("/get_collection_data/<string:collection_name>")
    @only_admin
    def get_collection_data(collection_name):
        model = TABLES.get(collection_name)
        if model is None or not require_db():
            return jsonify({"error": "Unknown table or database unavailable"}), 404
        rows = []
        for obj in model.query.order_by(model.id).limit(500).all():
            row = {}
            for col in model.__table__.columns:
                if col.name in HIDDEN_COLUMNS:
                    continue
                value = getattr(obj, col.name)
                row[col.name] = value.isoformat() if isinstance(value, datetime) else value
            row["_id"] = str(obj.id)
            rows.append(row)
        return jsonify(rows)

    @app.route("/admin/analyse")
    @only_admin
    def analyse():
        return render_template("admin/colab.html", admin=admin())
