from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import transaction

from app.administration.control_layer.permissions.template_assignment_guard import (
    assert_actor_may_edit_templates,
)
from app.administration.models import (
    PermissionGroupTemplate,
    PermissionGroupTemplateItem,
)

User = get_user_model()


class PermissionGroupTemplateContext:
    """Control entry for editing a single permission group template (id-keyed)."""

    def __init__(self, template_id: int) -> None:
        self.template_id = template_id
        self._template = PermissionGroupTemplate.objects.get(pk=template_id)

    @property
    def template(self) -> PermissionGroupTemplate:
        return self._template

    def refresh(self) -> None:
        self._template = PermissionGroupTemplate.objects.get(pk=self.template_id)

    @transaction.atomic
    def add_permission_group(self, *, actor: User, group_id: int) -> PermissionGroupTemplateItem:
        assert_actor_may_edit_templates(actor)
        group = Group.objects.get(pk=group_id)
        item, _created = PermissionGroupTemplateItem.objects.get_or_create(
            template=self._template,
            permission_group=group,
            defaults={"created_by": actor, "updated_by": actor},
        )
        return item

    @transaction.atomic
    def remove_permission_group(self, *, actor: User, group_id: int) -> None:
        assert_actor_may_edit_templates(actor)
        PermissionGroupTemplateItem.objects.filter(
            template=self._template,
            permission_group_id=group_id,
        ).delete()

    @transaction.atomic
    def set_active(self, *, actor: User, is_active: bool) -> PermissionGroupTemplate:
        assert_actor_may_edit_templates(actor)
        self._template.is_active = is_active
        self._template.updated_by = actor
        self._template.save(update_fields=["is_active", "updated_at", "updated_by"])
        return self._template

    @transaction.atomic
    def update_metadata(
        self,
        *,
        actor: User,
        name: str | None = None,
        description: str | None = None,
    ) -> PermissionGroupTemplate:
        assert_actor_may_edit_templates(actor)
        update_fields: list[str] = ["updated_at", "updated_by"]
        if name is not None:
            self._template.name = name
            update_fields.append("name")
        if description is not None:
            self._template.description = description
            update_fields.append("description")
        self._template.updated_by = actor
        self._template.save(update_fields=update_fields)
        return self._template
