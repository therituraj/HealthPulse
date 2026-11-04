"""Home dashboard, report generation (diabetes / heart), My Reports, view and PDF export."""
import logging
from io import BytesIO

from flask import (abort, current_app, flash, redirect, render_template, request, send_file, session, url_for)
from sqlalchemy.exc import SQLAlchemyError

from .. import health
from ..extensions import db, db_ready
from ..ml import ModelUnavailable, predict
from ..models import Report
from .helpers import current_user, login_required, require_db, route_enabled

log = logging.getLogger("healthpulse")
PER_PAGE = 10


def _own_report_or_404(public_id):
    user = current_user()
    return Report.query.filter_by(public_id=public_id, user_id=user["id"]).first_or_404()


def register(app):
    @app.route("/")
    def home():
        user = current_user()
        if not user:
            if session.get("admin"):
                return redirect(url_for("admin_dashboard"))
            return render_template("landing_page.html")
        reports, total, db_error = [], 0, False
        if db_ready():
            try:
                q = Report.query.filter_by(user_id=user["id"])
                total = q.count()
                reports = q.order_by(Report.created_at.desc()).limit(5).all()
            except SQLAlchemyError:
                db.session.rollback()
                db_error = True
        else:
            db_error = True
        return render_template("index.html", user=user, reports=reports, total=total, db_error=db_error)

    @app.route("/report/new")
    @login_required
    def new_report():
        return render_template("new_report.html", user=current_user())

    def _predict_view(kind, template):
        user = current_user()
        if request.method == "POST":
            clean, errors = health.validate(kind, request.form)
            if errors:
                for message in errors:
                    flash(message, "error")
                return render_template(template, user=user)
            if not require_db():
                return render_template(template, user=user)
            try:
                vector = health.features(kind, clean, current_app.config["HEART_AGE_IN_DAYS"])
                prediction, probability = predict(kind, vector)
            except ModelUnavailable:
                flash("The prediction model is not available right now. Please try again later.", "error")
                return render_template(template, user=user)
            report = Report(user_id=user["id"], kind=kind, inputs=clean, prediction=prediction, probability=probability)
            db.session.add(report)
            db.session.commit()
            return redirect(url_for("view_report", public_id=report.public_id))
        return render_template(template, user=user)

    @app.route("/diabetes", methods=["GET", "POST"])
    @login_required
    @route_enabled("diabetes")
    def diabetes():
        return _predict_view("diabetes", "diabetes.html")

    @app.route("/heart_diseases", methods=["GET", "POST"])
    @login_required
    @route_enabled("heart_diseases")
    def heart_diseases():
        return _predict_view("heart", "heart_diseases.html")

    @app.route("/my_reports")
    @login_required
    def my_reports():
        user = current_user()
        kind = request.args.get("kind", "all")
        page = request.args.get("page", 1, type=int)
        if kind not in ("all", "diabetes", "heart"):
            kind = "all"
        counts, pagination = {"all": 0, "diabetes": 0, "heart": 0}, None
        if require_db():
            try:
                base = Report.query.filter_by(user_id=user["id"])
                counts["diabetes"] = base.filter_by(kind="diabetes").count()
                counts["heart"] = base.filter_by(kind="heart").count()
                counts["all"] = counts["diabetes"] + counts["heart"]
                q = base if kind == "all" else base.filter_by(kind=kind)
                pagination = q.order_by(Report.created_at.desc()).paginate(page=page, per_page=PER_PAGE, error_out=False)
            except SQLAlchemyError:
                db.session.rollback()
                flash("Could not load your reports right now.", "error")
        return render_template("my_report.html", user=user, pagination=pagination, kind=kind, counts=counts)

    @app.route("/report/<public_id>")
    @login_required
    def view_report(public_id):
        if not require_db():
            return redirect(url_for("my_reports"))
        report = _own_report_or_404(public_id)
        sections = health.grouped_rows(report.kind, report.inputs or {})
        headline = health.RESULT_TEXT[report.kind][0 if report.is_high_risk else 1]
        return render_template("report_view.html", user=current_user(), report=report, sections=sections,
                               headline=headline)

    @app.route("/report/<public_id>/pdf")
    @login_required
    def report_pdf(public_id):
        if not require_db():
            return redirect(url_for("my_reports"))
        report = _own_report_or_404(public_id)
        try:
            from ..pdf import build_report_pdf

            data = build_report_pdf(report, current_user()["name"], health.grouped_rows(report.kind, report.inputs or {}))
        except Exception:  # noqa: BLE001
            log.exception("PDF export failed")
            flash("Could not create the PDF right now. Please try again.", "error")
            return redirect(url_for("view_report", public_id=public_id))
        return send_file(BytesIO(data), mimetype="application/pdf", as_attachment=True,
                         download_name=f"healthpulse-{report.kind}-report-{report.public_id}.pdf")

    @app.route("/report/<public_id>/delete", methods=["POST"])
    @login_required
    def delete_report(public_id):
        if not require_db():
            return redirect(url_for("my_reports"))
        report = _own_report_or_404(public_id)
        db.session.delete(report)
        db.session.commit()
        flash("Report deleted.", "success")
        return redirect(url_for("my_reports"))
