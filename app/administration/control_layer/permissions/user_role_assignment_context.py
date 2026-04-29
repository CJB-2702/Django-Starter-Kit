from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import transaction

from app.administration.control_layer.permissions.permission_grant_guard import (
    assert_can_manage_target,
)
from app.administration.control_layer.permissions.role_assignment_guard import (
    assert_actor_may_assign_roles,
)
from app.administration.control_layer.permissions.role_rebase_handler import (
    RoleRebaseHandler,
)
from app.administration.models import Role, UserRole

User = get_user_model()


class UserRoleAssignmentContext:
    """Control entry for a user's active role assignments (zero or more)."""

    def __init__(self, target_user_id: int) -> None:
        self.target_user_id = target_user_id

    def _active_assignments(self):
        return UserRole.objects.filter(
            user_id=self.target_user_id,
            is_active=True,
        ).select_related("role")

    @transaction.atomic
    def assign_role(
        self,
        *,
        actor: User,
        role_id: int,
        relationship_type: str = UserRole.RelationshipType.PRIMARY,
        notes: str = "",
    ) -> UserRole:
        target = User.objects.get(pk=self.target_user_id)
        assert_can_manage_target(actor, target)
        role = Role.objects.get(pk=role_id)
        if not role.is_active:
            from app.administration.control_layer.permissions.permission_grant_guard import (
                GrantPermissionDenied,
            )
            raise GrantPermissionDenied("Cannot assign an inactive role.")
        assert_actor_may_assign_roles(actor, role=role)

        assignment, _created = UserRole.objects.get_or_create(
            user=target,
            role=role,
            defaults={
                "relationship_type": relationship_type,
                "notes": notes,
                "is_active": True,
                "created_by": actor,
                "updated_by": actor,
            },
        )

        if not _created and not assignment.is_active:
            assignment.is_active = True
            assignment.relationship_type = relationship_type
            assignment.notes = notes
            assignment.updated_by = actor
            assignment.save(
                update_fields=[
                    "is_active",
                    "relationship_type",
                    "notes",
                    "updated_at",
                    "updated_by",
                ]
            )

        handler = RoleRebaseHandler(user=target)
        handler.sync()

        return assignment

    @transaction.atomic
    def remove_role(self, *, actor: User, role_id: int) -> None:
        target = User.objects.get(pk=self.target_user_id)
        assert_can_manage_target(actor, target)
        role = Role.objects.get(pk=role_id)
        assert_actor_may_assign_roles(actor, role=role)

        try:
            assignment = UserRole.objects.get(
                user=target,
                role=role,
                is_active=True,
            )
            assignment.is_active = False
            assignment.updated_by = actor
            assignment.save(update_fields=["is_active", "updated_at", "updated_by"])
        except UserRole.DoesNotExist:
            pass

        handler = RoleRebaseHandler(user=target)
        handler.sync()

    @transaction.atomic
    def update_notes(
        self,
        *,
        actor: User,
        role_id: int,
        notes: str,
    ) -> UserRole | None:
        target = User.objects.get(pk=self.target_user_id)
        assert_can_manage_target(actor, target)
        try:
            assignment = UserRole.objects.get(
                user=target,
                role_id=role_id,
                is_active=True,
            )
            assignment.notes = notes
            assignment.updated_by = actor
            assignment.save(update_fields=["notes", "updated_at", "updated_by"])
            return assignment
        except UserRole.DoesNotExist:
            return None

    @transaction.atomic
    def update_relationship_type(
        self,
        *,
        actor: User,
        role_id: int,
        relationship_type: str,
    ) -> UserRole | None:
        target = User.objects.get(pk=self.target_user_id)
        assert_can_manage_target(actor, target)
        try:
            assignment = UserRole.objects.get(
                user=target,
                role_id=role_id,
                is_active=True,
            )
            assignment.relationship_type = relationship_type
            assignment.updated_by = actor
            assignment.save(
                update_fields=["relationship_type", "updated_at", "updated_by"]
            )
            return assignment
        except UserRole.DoesNotExist:
            return None
