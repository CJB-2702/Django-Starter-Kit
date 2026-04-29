from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from app.administration.models import (
    PermissionGroupTemplate,
    PermissionGroupTemplateItem,
    UserPermissionGroupTemplate,
)

User = get_user_model()


@dataclass
class TemplateDriftStruct:
    """Read aggregate: a user's active template, its expected groups, and drift."""

    user_id: int
    assignment: UserPermissionGroupTemplate | None = None
    template: PermissionGroupTemplate | None = None
    notes: str = ""
    expected_group_ids: frozenset[int] = field(default_factory=frozenset)
    actual_group_ids: frozenset[int] = field(default_factory=frozenset)
    drift_added_groups: list[Group] = field(default_factory=list)
    drift_removed_groups: list[Group] = field(default_factory=list)

    @property
    def has_template(self) -> bool:
        return self.template is not None

    @property
    def has_drift(self) -> bool:
        return bool(self.drift_added_groups) or bool(self.drift_removed_groups)

    @property
    def has_notes(self) -> bool:
        return bool(self.notes.strip())

    @classmethod
    def load(cls, user_id: int) -> TemplateDriftStruct:
        user = User.objects.get(pk=user_id)
        try:
            assignment = (
                UserPermissionGroupTemplate.objects.select_related("template")
                .get(user=user)
            )
        except UserPermissionGroupTemplate.DoesNotExist:
            assignment = None

        actual_group_ids = frozenset(user.groups.values_list("pk", flat=True))

        if assignment is None:
            return cls(
                user_id=user_id,
                actual_group_ids=actual_group_ids,
            )

        template = assignment.template
        expected_group_ids = frozenset(
            PermissionGroupTemplateItem.objects.filter(template=template).values_list(
                "permission_group_id",
                flat=True,
            ),
        )
        drift_added_ids = sorted(actual_group_ids - expected_group_ids)
        drift_removed_ids = sorted(expected_group_ids - actual_group_ids)
        added = list(Group.objects.filter(pk__in=drift_added_ids).order_by("name"))
        removed = list(Group.objects.filter(pk__in=drift_removed_ids).order_by("name"))

        return cls(
            user_id=user_id,
            assignment=assignment,
            template=template,
            notes=assignment.notes,
            expected_group_ids=expected_group_ids,
            actual_group_ids=actual_group_ids,
            drift_added_groups=added,
            drift_removed_groups=removed,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "template": (
                {"id": self.template.pk, "name": self.template.name, "slug": self.template.slug}
                if self.template
                else None
            ),
            "notes": self.notes,
            "has_template": self.has_template,
            "has_drift": self.has_drift,
            "has_notes": self.has_notes,
            "expected_group_ids": sorted(self.expected_group_ids),
            "actual_group_ids": sorted(self.actual_group_ids),
            "drift_added_group_names": [g.name for g in self.drift_added_groups],
            "drift_removed_group_names": [g.name for g in self.drift_removed_groups],
        }
