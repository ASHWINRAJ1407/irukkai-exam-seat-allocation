"""Subscription helpers (simplified).

Subscriptions and payment-related flows have been removed. This module now
provides a minimal permission check (requires login) and optional usage
recording via `UsageEvent`.
"""

from models import db, UsageEvent


def is_feature_allowed(user, feature: str, free_limit: int = 0):
    """Allow features for any authenticated user. Returns (allowed, message).

    The app no longer enforces subscriptions; authenticated users are allowed
    to use features.
    """
    if not user or not getattr(user, "id", None):
        return False, "Please log in to use this feature."
    return True, ""


def record_usage(user, feature: str):
    """Persist a usage event (optional)."""
    if not user or not getattr(user, "id", None):
        return
    try:
        ev = UsageEvent(user_id=user.id, feature=feature)
        db.session.add(ev)
        db.session.commit()
    except Exception:
        db.session.rollback()

