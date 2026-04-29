"""
Policy: who may edit and assign roles.

Guard type: **Policy** — authorization gate for role management and role
assignment to users.
"""

from __future__ import annotations

from django.contrib.auth.models import User

from app.administration.control_layer.permissions.permission_grant_guard import (
    GrantPermissionDenied,
    assert_actor_may_add_groups,
    is_admin_actor,
)
from app.administration.models import Role


def assert_actor_may_edit_roles(actor: User) -> None:
    """Only admins (superusers + generic_admin members) may create or edit roles."""
    if not is_admin_actor(actor):
        raise GrantPermissionDenied(
            "Only generic_admin or Django superusers may edit roles.",
        )


def assert_actor_may_assign_roles(actor: User, *, role: Role) -> None:
    """
    Admin always allowed; managers must hold every permission reachable through
    every group in the role (transitive permission gate).
    """
    if is_admin_actor(actor):
        return
    groups = [item.permission_group for item in role.items.select_related("permission_group")]
    assert_actor_may_add_groups(actor, groups_to_add=groups)
