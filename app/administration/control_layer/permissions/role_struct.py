from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from django.contrib.auth import get_user_model

from app.administration.models import Role, UserRole

User = get_user_model()


@dataclass
class RoleAssignmentItem:
    """One role assignment for a user."""
    role_id: int
    role_name: str
    relationship_type: str
    notes: str
    parent_role_id: int | None = None
    parent_role_name: str | None = None


@dataclass
class RoleStruct:
    """Read aggregate: a user's active role assignments and effective permission groups."""

    user_id: int
    active_role_assignments: list[RoleAssignmentItem] = field(default_factory=list)
    effective_group_ids: frozenset[int] = field(default_factory=frozenset)
    effective_group_names: list[str] = field(default_factory=list)

    @property
    def has_roles(self) -> bool:
        return bool(self.active_role_assignments)

    @classmethod
    def load(cls, user_id: int) -> RoleStruct:
        user = User.objects.get(pk=user_id)
        assignments = UserRole.objects.filter(
            user=user,
            is_active=True,
        ).select_related("role", "role__parent_role")

        role_items = []
        for assignment in assignments:
            role_items.append(
                RoleAssignmentItem(
                    role_id=assignment.role_id,
                    role_name=assignment.role.name,
                    relationship_type=assignment.relationship_type,
                    notes=assignment.notes,
                    parent_role_id=assignment.role.parent_role_id,
                    parent_role_name=assignment.role.parent_role.name if assignment.role.parent_role else None,
                )
            )

        from app.administration.control_layer.permissions.role_rebase_handler import RoleRebaseHandler
        effective_ids = RoleRebaseHandler._compute_effective_group_ids(user)

        from django.contrib.auth.models import Group
        effective_groups = Group.objects.filter(pk__in=effective_ids).order_by("name")
        effective_names = [g.name for g in effective_groups]

        return cls(
            user_id=user_id,
            active_role_assignments=role_items,
            effective_group_ids=frozenset(effective_ids),
            effective_group_names=effective_names,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "has_roles": self.has_roles,
            "active_role_assignments": [
                {
                    "role_id": assignment.role_id,
                    "role_name": assignment.role_name,
                    "relationship_type": assignment.relationship_type,
                    "notes": assignment.notes,
                    "parent_role_id": assignment.parent_role_id,
                    "parent_role_name": assignment.parent_role_name,
                }
                for assignment in self.active_role_assignments
            ],
            "effective_group_names": self.effective_group_names,
        }
