from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.db import transaction

from app.administration.control_layer.permission_grant_policy import (
    assert_actor_may_add_groups,
    assert_actor_may_add_permissions,
    assert_actor_may_remove_groups,
    assert_actor_may_remove_permissions,
    assert_can_manage_target,
)
from app.administration.control_layer.domain_structs.user_django_permissions_struct import (
    UserDjangoPermissionsStruct,
)

User = get_user_model()


class DjangoPermissionsContext:
    """Control entry for Django ``Group`` and direct ``Permission`` membership."""

    def __init__(self, target_user_id: int) -> None:
        self.target_user_id = target_user_id
        self._struct = UserDjangoPermissionsStruct.load(target_user_id)

    @classmethod
    def from_struct(cls, struct: UserDjangoPermissionsStruct) -> DjangoPermissionsContext:
        ctx = cls(struct.user_id)
        ctx._struct = struct
        return ctx

    @property
    def struct(self) -> UserDjangoPermissionsStruct:
        return self._struct

    def refresh_struct(self) -> None:
        self._struct = UserDjangoPermissionsStruct.load(self.target_user_id)

    @transaction.atomic
    def add_group(self, *, actor: User, group_id: int) -> None:
        target = User.objects.get(pk=self.target_user_id)
        assert_can_manage_target(actor, target)
        group = Group.objects.get(pk=group_id)
        assert_actor_may_add_groups(actor, groups_to_add=[group])
        target.groups.add(group)
        self.refresh_struct()

    @transaction.atomic
    def remove_group(self, *, actor: User, group_id: int) -> None:
        target = User.objects.get(pk=self.target_user_id)
        assert_can_manage_target(actor, target)
        group = Group.objects.get(pk=group_id)
        assert_actor_may_remove_groups(actor, groups_to_remove=[group])
        target.groups.remove(group)
        self.refresh_struct()

    @transaction.atomic
    def add_direct_permission(self, *, actor: User, permission_id: int) -> None:
        target = User.objects.get(pk=self.target_user_id)
        assert_can_manage_target(actor, target)
        perm = Permission.objects.select_related("content_type").get(pk=permission_id)
        assert_actor_may_add_permissions(actor, permissions_to_add=[perm])
        target.user_permissions.add(perm)
        self.refresh_struct()

    @transaction.atomic
    def remove_direct_permission(self, *, actor: User, permission_id: int) -> None:
        target = User.objects.get(pk=self.target_user_id)
        assert_can_manage_target(actor, target)
        perm = Permission.objects.select_related("content_type").get(pk=permission_id)
        assert_actor_may_remove_permissions(actor, permissions_to_remove=[perm])
        target.user_permissions.remove(perm)
        self.refresh_struct()
