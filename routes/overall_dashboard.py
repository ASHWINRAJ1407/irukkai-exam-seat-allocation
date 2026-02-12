"""Admin-only user approval dashboard.

This dashboard is the only cross-tenant view. It shows only user identities and
approval status (not any business data like departments/students/etc).
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, User

overall_dashboard_bp = Blueprint("overall_dashboard", __name__)


def _require_admin():
    if not getattr(current_user, "is_admin", False):
        flash("Access denied.", "danger")
        return False
    return True


@overall_dashboard_bp.route("/overall", methods=["GET"])
@login_required
def overall():
    if not _require_admin():
        return redirect(url_for("dashboard.index"))
    users = (
        User.query.filter(User.is_admin.is_(False))
        .order_by(User.created_at.desc())
        .all()
    )
    return render_template("admin/overall_dashboard.html", users=users)


@overall_dashboard_bp.route("/overall/update/<int:user_db_id>", methods=["POST"])
@login_required
def update_user_status(user_db_id: int):
    if not _require_admin():
        return redirect(url_for("dashboard.index"))

    action = (request.form.get("action") or "").strip().lower()
    user = User.query.get_or_404(user_db_id)

    if user.is_admin:
        flash("Admin account status cannot be changed here.", "warning")
        return redirect(url_for("overall_dashboard.overall"))

    if action == "approve":
        user.account_status = "approved"
        db.session.commit()
        flash(f'Approved "{user.user_id}".', "success")
    elif action == "reject":
        user.account_status = "rejected"
        db.session.commit()
        flash(f'Rejected "{user.user_id}".', "warning")
    elif action == "revoke":
        user.account_status = "revoked"
        db.session.commit()
        flash(f'Revoked access for "{user.user_id}".', "warning")
    else:
        flash("Unknown action.", "danger")

    return redirect(url_for("overall_dashboard.overall"))

