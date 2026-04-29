from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.db.models import Prefetch

User = get_user_model()


@dataclass
class UserDjangoPermissionsStruct:
    """Effective Django permissions and group membership for display and checks."""

    user_id: int
    group_names: list[str] = field(default_factory=list)
    direct_permission_keys: list[str] = field(default_factory=list)
    effective_permission_keys: frozenset[str] = field(default_factory=frozenset)
    effective_permission_keys_sorted: list[str] = field(default_factory=list)
    group_permission_rows: list[tuple[str, list[str]]] = field(default_factory=list)

    @classmethod
    def load(cls, user_id: int) -> UserDjangoPermissionsStruct:
        perm_ordered = Permission.objects.select_related("content_type").order_by(
            "content_type__app_label",
            "content_type__model",
            "codename",
        )
        groups_qs = Group.objects.order_by("name").prefetch_related(
            Prefetch("permissions", queryset=perm_ordered),
        )
        user = User.objects.prefetch_related(
            Prefetch("groups", queryset=groups_qs),
            Prefetch("user_permissions", queryset=perm_ordered),
        ).get(pk=user_id)

        group_permission_rows: list[tuple[str, list[str]]] = []
        for g in user.groups.order_by("name"):
            keys = sorted(
                f"{p.content_type.app_label}.{p.codename}" for p in g.permissions.all()
            )
            group_permission_rows.append((g.name, keys))

        group_names = [name for name, _ in group_permission_rows]

        direct = user.user_permissions.all()
        direct_keys = sorted(
            f"{p.content_type.app_label}.{p.codename}" for p in direct
        )
        effective = frozenset(user.get_all_permissions())
        effective_sorted = sorted(effective)
        return cls(
            user_id=user_id,
            group_names=group_names,
            direct_permission_keys=direct_keys,
            effective_permission_keys=effective,
            effective_permission_keys_sorted=effective_sorted,
            group_permission_rows=group_permission_rows,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "group_names": self.group_names,
            "direct_permission_keys": self.direct_permission_keys,
            "effective_permission_keys": self.effective_permission_keys_sorted,
            "group_permission_rows": [
                {"name": name, "permission_keys": keys}
                for name, keys in self.group_permission_rows
            ],
        }
