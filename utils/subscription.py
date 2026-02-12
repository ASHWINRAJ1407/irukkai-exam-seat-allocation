"""Subscription and freemium usage helpers."""

from datetime import date
from flask import current_app
from models import db, Subscription, SubscriptionPlan, UsageEvent


def _get_active_subscription(user):
    """Return active subscription for a user, if any."""
    if not user or not getattr(user, "id", None):
        return None
    today = date.today()
    return (
        Subscription.query.filter(
            Subscription.user_id == user.id,
            Subscription.start_date <= today,
            Subscription.end_date >= today,
        )
        .order_by(Subscription.end_date.desc())
        .first()
    )


def is_feature_allowed(user, feature: str, free_limit: int = 3):
    """Return (allowed: bool, message: str) for the given feature."""
    if not user or not getattr(user, "id", None):
        return False, "Please log in to use this feature."
    if getattr(user, "is_admin", False):
        return True, ""

    # If user has an active subscription, allow unlimited usage.
    if _get_active_subscription(user):
        return True, ""

    # Freemium: allow only a limited number of total feature invocations.
    used = UsageEvent.query.filter(UsageEvent.user_id == user.id).count()
    if used >= free_limit:
        return (
            False,
            "Free usage limit reached. Please submit payment details and choose a subscription plan to continue.",
        )
    return True, ""


def record_usage(user, feature: str):
    """Persist a usage event for the given feature."""
    if not user or not getattr(user, "id", None):
        return
    ev = UsageEvent(user_id=user.id, feature=feature)
    db.session.add(ev)
    db.session.commit()

