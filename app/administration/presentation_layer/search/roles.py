"""Search and loading functions for roles."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db.models import QuerySet

from app.administration.control_layer.permissions.role_struct import RoleStruct
from app.administration.models import Role

User = get_user_model()


def list_roles(*, include_inactive: bool = False) -> QuerySet[Role]:
    """Load all roles (active by default)."""
    qs = Role.objects.prefetch_related("items__permission_group").select_related(
        "parent_role"
    )
    if not include_inactive:
        qs = qs.filter(is_active=True)
    return qs.order_by("name")


def load_user_role_struct(user_id: int) -> RoleStruct:
    """Load a read-only aggregate of user's active roles and effective permission groups."""
    return RoleStruct.load(user_id)
