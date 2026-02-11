"""Subscription and payment management routes."""

from datetime import date, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, AdminSettings, SubscriptionPlan, Subscription, PaymentSubmission

subscriptions_bp = Blueprint("subscriptions", __name__)


@subscriptions_bp.route("/subscriptions", methods=["GET"])
@login_required
def plans():
    """Show available plans, current subscription, and bank/payment details."""
    settings = AdminSettings.query.get(1)
    plans = SubscriptionPlan.query.filter_by(is_active=True).order_by(SubscriptionPlan.id).all()

    today = date.today()
    current_sub = (
        Subscription.query.filter(
            Subscription.user_id == current_user.id,
            Subscription.start_date <= today,
            Subscription.end_date >= today,
        )
        .order_by(Subscription.end_date.desc())
        .first()
    )
    submissions = PaymentSubmission.query.filter_by(user_id=current_user.id).order_by(
        PaymentSubmission.created_at.desc()
    ).all()

    return render_template(
        "subscriptions/plans.html",
        settings=settings,
        plans=plans,
        current_subscription=current_sub,
        submissions=submissions,
    )


@subscriptions_bp.route("/subscriptions/submit", methods=["POST"])
@login_required
def submit_payment():
    """User submits a payment reference for a chosen plan."""
    plan_id = request.form.get("plan_id")
    reference = (request.form.get("reference") or "").strip()
    if not plan_id or not reference:
        flash("Please choose a plan and enter a payment reference / UTR.", "danger")
        return redirect(url_for("subscriptions.plans"))
    plan = SubscriptionPlan.query.get(plan_id)
    if not plan or not plan.is_active:
        flash("Invalid or inactive subscription plan.", "danger")
        return redirect(url_for("subscriptions.plans"))
    ps = PaymentSubmission(user_id=current_user.id, plan_id=plan.id, reference=reference, status="pending")
    db.session.add(ps)
    db.session.commit()
    flash("Payment submitted for review. The administrator will verify and activate your subscription.", "success")
    return redirect(url_for("subscriptions.plans"))


@subscriptions_bp.route("/subscriptions/admin", methods=["GET"])
@login_required
def admin_index():
    """Admin view: review payment submissions and active subscriptions."""
    if not current_user.is_admin:
        flash("Access denied.", "danger")
        return redirect(url_for("dashboard.index"))
    pending = PaymentSubmission.query.filter_by(status="pending").order_by(
        PaymentSubmission.created_at.asc()
    ).all()
    recent = PaymentSubmission.query.filter(PaymentSubmission.status != "pending").order_by(
        PaymentSubmission.created_at.desc()
    ).limit(50).all()
    subs = Subscription.query.order_by(Subscription.end_date.desc()).limit(50).all()
    plans = {p.id: p for p in SubscriptionPlan.query.all()}
    return render_template(
        "subscriptions/admin_index.html",
        pending=pending,
        recent=recent,
        subscriptions=subs,
        plans=plans,
    )


@subscriptions_bp.route("/subscriptions/admin/update/<int:submission_id>", methods=["POST"])
@login_required
def admin_update_submission(submission_id):
    """Approve or reject a payment submission."""
    if not current_user.is_admin:
        flash("Access denied.", "danger")
        return redirect(url_for("dashboard.index"))
    action = request.form.get("action")
    note = (request.form.get("admin_note") or "").strip()
    ps = PaymentSubmission.query.get_or_404(submission_id)
    plan = SubscriptionPlan.query.get(ps.plan_id)
    if not plan:
        flash("Plan not found for this submission.", "danger")
        return redirect(url_for("subscriptions.admin_index"))
    if action == "approve":
        # Create or extend subscription
        today = date.today()
        start = today
        end = today + timedelta(days=30 * plan.duration_months)
        sub = Subscription(user_id=ps.user_id, plan_id=plan.id, start_date=start, end_date=end)
        db.session.add(sub)
        ps.status = "approved"
        ps.processed_at = date.today()
        ps.admin_note = note or f"Approved for plan {plan.name}"
        db.session.commit()
        flash("Subscription activated successfully.", "success")
    elif action == "reject":
        ps.status = "rejected"
        ps.processed_at = date.today()
        ps.admin_note = note or "Rejected"
        db.session.commit()
        flash("Submission marked as rejected.", "info")
    else:
        flash("Unknown action.", "danger")
    return redirect(url_for("subscriptions.admin_index"))


@subscriptions_bp.route("/subscriptions/admin/settings", methods=["GET", "POST"])
@login_required
def admin_settings():
    """Admin view: configure bank account and payment instructions."""
    if not current_user.is_admin:
        flash("Access denied.", "danger")
        return redirect(url_for("dashboard.index"))
    settings = AdminSettings.query.get(1)
    if request.method == "POST":
        bank_details = request.form.get("bank_details") or ""
        instructions = request.form.get("payment_instructions") or ""
        if not settings:
            settings = AdminSettings(id=1)
            db.session.add(settings)
        settings.bank_details = bank_details
        settings.payment_instructions = instructions
        db.session.commit()
        flash("Payment settings updated.", "success")
        return redirect(url_for("subscriptions.admin_settings"))
    return render_template("subscriptions/admin_settings.html", settings=settings)

