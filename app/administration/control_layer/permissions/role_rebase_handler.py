"""Handler: sync a user's auth.Group membership to their active roles (union semantics)."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from app.administration.models import Role, RoleItem, UserRole

User = get_user_model()


class RoleRebaseHandler:
    """One complex step: align user.groups to the union of all active roles."""

    def __init__(self, user: User) -> None:
        self.user = user

    @staticmethod
    def _compute_effective_group_ids(user: User) -> set[int]:
        """Compute all permission group ids from the user's active roles (including parent roles)."""
        active_roles = UserRole.objects.filter(
            user=user,
            is_active=True,
        ).values_list("role_id", flat=True)

        if not active_roles:
            return set()

        role_ids = set(active_roles)
        all_role_ids = set(active_roles)

        for role_id in active_roles:
            role = Role.objects.get(pk=role_id)
            if role.parent_role_id and role.parent_role_id not in all_role_ids:
                all_role_ids.add(role.parent_role_id)

        return set(
            RoleItem.objects.filter(role_id__in=all_role_ids).values_list(
                "permission_group_id",
                flat=True,
            ),
        )

    def sync(self) -> None:
        """Update user.groups to the union of all active role permission groups."""
        effective_ids = self._compute_effective_group_ids(self.user)
        current_ids = set(self.user.groups.values_list("pk", flat=True))

        to_remove = current_ids - effective_ids
        if to_remove:
            self.user.groups.remove(*Group.objects.filter(pk__in=to_remove))

        to_add = effective_ids - current_ids
        if to_add:
            self.user.groups.add(*Group.objects.filter(pk__in=to_add))
