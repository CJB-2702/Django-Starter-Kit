"""Handler: sync a user's auth.Group membership to a permission group template."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from app.administration.models import (
    PermissionGroupTemplate,
    PermissionGroupTemplateItem,
)

User = get_user_model()


class TemplateRebaseHandler:
    """One complex step: align ``user.groups`` with a template (rebase or additive)."""

    def __init__(
        self,
        *,
        user: User,
        new_template: PermissionGroupTemplate,
        previous_template: PermissionGroupTemplate | None,
    ) -> None:
        self.user = user
        self.new_template = new_template
        self.previous_template = previous_template

    @staticmethod
    def _template_group_ids(template: PermissionGroupTemplate | None) -> set[int]:
        if template is None:
            return set()
        return set(
            PermissionGroupTemplateItem.objects.filter(template=template).values_list(
                "permission_group_id",
                flat=True,
            ),
        )

    def rebase(self) -> None:
        """Strip groups from the previous template and apply the new template's groups."""
        previous_ids = self._template_group_ids(self.previous_template)
        new_ids = self._template_group_ids(self.new_template)

        if previous_ids:
            to_remove = previous_ids - new_ids
            if to_remove:
                self.user.groups.remove(*Group.objects.filter(pk__in=to_remove))

        to_add = new_ids - set(self.user.groups.values_list("pk", flat=True))
        if to_add:
            self.user.groups.add(*Group.objects.filter(pk__in=to_add))

    def additive(self) -> None:
        """Apply the new template's groups without removing the previous template's groups."""
        new_ids = self._template_group_ids(self.new_template)
        to_add = new_ids - set(self.user.groups.values_list("pk", flat=True))
        if to_add:
            self.user.groups.add(*Group.objects.filter(pk__in=to_add))
