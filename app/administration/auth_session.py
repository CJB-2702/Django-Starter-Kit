"""Snapshot user ownership groups and Django permissions into the session at login."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.contrib.auth.base_user import AbstractBaseUser
    from django.http import HttpRequest

SESSION_KEY_OWNERSHIP_GROUP_IDS = "user_ownership_group_ids"
SESSION_KEY_PERMISSION_CODENAMES = "user_permission_codenames"


def refresh_auth_in_session(request: HttpRequest, user: AbstractBaseUser) -> None:
    """Store active ownership group ids and effective permission strings on the session."""
    from django.contrib.auth.models import AnonymousUser

    from app.administration.models import UserOwnershipGroup

    if not getattr(user, "is_active", True) or isinstance(user, AnonymousUser):
        request.session.pop(SESSION_KEY_OWNERSHIP_GROUP_IDS, None)
        request.session.pop(SESSION_KEY_PERMISSION_CODENAMES, None)
        return

    og_ids = list(
        UserOwnershipGroup.objects.filter(user=user).values_list(
            "ownership_group_id",
            flat=True,
        )
    )
    perms = sorted(user.get_all_permissions())
    request.session[SESSION_KEY_OWNERSHIP_GROUP_IDS] = og_ids
    request.session[SESSION_KEY_PERMISSION_CODENAMES] = perms


def session_ownership_group_ids(request: HttpRequest) -> list[int]:
    """Ownership group primary keys from the last login snapshot, or []."""
    raw = request.session.get(SESSION_KEY_OWNERSHIP_GROUP_IDS)
    if raw is None:
        return []
    return list(raw)


def session_permission_codenames(request: HttpRequest) -> frozenset[str]:
    """Effective Django permission strings from the last login snapshot, or empty."""
    raw = request.session.get(SESSION_KEY_PERMISSION_CODENAMES)
    if raw is None:
        return frozenset()
    return frozenset(raw)
