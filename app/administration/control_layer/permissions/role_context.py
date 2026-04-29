from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import transaction

from app.administration.control_layer.permissions.role_assignment_guard import (
    assert_actor_may_edit_roles,
)
from app.administration.models import Role, RoleItem

User = get_user_model()


class RoleContext:
    """Control entry for editing a single role (id-keyed)."""

    def __init__(self, role_id: int) -> None:
        self.role_id = role_id
        self._role = Role.objects.get(pk=role_id)

    @property
    def role(self) -> Role:
        return self._role

    def refresh(self) -> None:
        self._role = Role.objects.get(pk=self.role_id)

    @transaction.atomic
    def add_permission_group(self, *, actor: User, group_id: int) -> RoleItem:
        assert_actor_may_edit_roles(actor)
        group = Group.objects.get(pk=group_id)
        item, _created = RoleItem.objects.get_or_create(
            role=self._role,
            permission_group=group,
            defaults={"created_by": actor, "updated_by": actor},
        )
        return item

    @transaction.atomic
    def remove_permission_group(self, *, actor: User, group_id: int) -> None:
        assert_actor_may_edit_roles(actor)
        RoleItem.objects.filter(
            role=self._role,
            permission_group_id=group_id,
        ).delete()

    @transaction.atomic
    def set_active(self, *, actor: User, is_active: bool) -> Role:
        assert_actor_may_edit_roles(actor)
        self._role.is_active = is_active
        self._role.updated_by = actor
        self._role.save(update_fields=["is_active", "updated_at", "updated_by"])
        return self._role

    @transaction.atomic
    def update_metadata(
        self,
        *,
        actor: User,
        name: str | None = None,
        description: str | None = None,
    ) -> Role:
        assert_actor_may_edit_roles(actor)
        update_fields: list[str] = ["updated_at", "updated_by"]
        if name is not None:
            self._role.name = name
            update_fields.append("name")
        if description is not None:
            self._role.description = description
            update_fields.append("description")
        self._role.updated_by = actor
        self._role.save(update_fields=update_fields)
        return self._role

    @transaction.atomic
    def set_parent_role(self, *, actor: User, parent_role_id: int | None) -> Role:
        assert_actor_may_edit_roles(actor)
        if parent_role_id is not None:
            parent_role = Role.objects.get(pk=parent_role_id)
            self._role.parent_role = parent_role
        else:
            self._role.parent_role = None
        self._role.updated_by = actor
        self._role.save(update_fields=["parent_role", "updated_at", "updated_by"])
        return self._role
