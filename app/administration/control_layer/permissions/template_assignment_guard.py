"""
Policy: who may edit and assign permission group templates.

Guard type: **Policy** — authorization gate for template management and template
assignment to users.
"""

from __future__ import annotations

from django.contrib.auth.models import User

from app.administration.control_layer.permissions.permission_grant_guard import (
    GrantPermissionDenied,
    assert_actor_may_add_groups,
    is_admin_actor,
)
from app.administration.models import PermissionGroupTemplate


def assert_actor_may_edit_templates(actor: User) -> None:
    """Only admins (superusers + generic_admin members) may create or edit templates."""
    if not is_admin_actor(actor):
        raise GrantPermissionDenied(
            "Only generic_admin or Django superusers may edit permission group templates.",
        )


def assert_actor_may_assign_template(actor: User, *, template: PermissionGroupTemplate) -> None:
    """
    Admin always allowed; managers must hold every permission reachable through
    every group in the template (transitive permission gate).
    """
    if is_admin_actor(actor):
        return
    groups = [item.permission_group for item in template.items.select_related("permission_group")]
    assert_actor_may_add_groups(actor, groups_to_add=groups)
