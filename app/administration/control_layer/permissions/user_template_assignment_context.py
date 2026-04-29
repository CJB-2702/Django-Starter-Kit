from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import transaction

from app.administration.control_layer.permissions.permission_grant_guard import (
    assert_can_manage_target,
)
from app.administration.control_layer.permissions.template_assignment_guard import (
    assert_actor_may_assign_template,
)
from app.administration.control_layer.permissions.template_rebase_handler import (
    TemplateRebaseHandler,
)
from app.administration.models import (
    PermissionGroupTemplate,
    UserPermissionGroupTemplate,
)

User = get_user_model()


class UserTemplateAssignmentContext:
    """Control entry for a user's active permission group template assignment."""

    def __init__(self, target_user_id: int) -> None:
        self.target_user_id = target_user_id

    def _active_assignment(self) -> UserPermissionGroupTemplate | None:
        try:
            return UserPermissionGroupTemplate.objects.select_related("template").get(
                user_id=self.target_user_id,
            )
        except UserPermissionGroupTemplate.DoesNotExist:
            return None

    @transaction.atomic
    def assign_template(
        self,
        *,
        actor: User,
        template_id: int,
        notes: str = "",
        additive: bool = False,
    ) -> UserPermissionGroupTemplate:
        target = User.objects.get(pk=self.target_user_id)
        assert_can_manage_target(actor, target)
        new_template = PermissionGroupTemplate.objects.get(pk=template_id)
        if not new_template.is_active:
            from app.administration.control_layer.permissions.permission_grant_guard import (
                GrantPermissionDenied,
            )
            raise GrantPermissionDenied("Cannot assign an inactive template.")
        assert_actor_may_assign_template(actor, template=new_template)

        previous = self._active_assignment()
        previous_template = previous.template if previous is not None else None

        if previous is not None:
            previous.is_active = False
            previous.updated_by = actor
            previous.save(update_fields=["is_active", "updated_at", "updated_by"])

        row = UserPermissionGroupTemplate.all_objects.create(
            user=target,
            template=new_template,
            notes=notes,
            is_active=True,
            created_by=actor,
            updated_by=actor,
        )

        handler = TemplateRebaseHandler(
            user=target,
            new_template=new_template,
            previous_template=previous_template,
        )
        if additive:
            handler.additive()
        else:
            handler.rebase()

        return row

    @transaction.atomic
    def re_rebase_current(self, *, actor: User) -> UserPermissionGroupTemplate | None:
        """Sync the user's groups to the currently assigned template (no swap)."""
        target = User.objects.get(pk=self.target_user_id)
        assert_can_manage_target(actor, target)
        current = self._active_assignment()
        if current is None:
            return None
        assert_actor_may_assign_template(actor, template=current.template)
        TemplateRebaseHandler(
            user=target,
            new_template=current.template,
            previous_template=current.template,
        ).rebase()
        return current

    @transaction.atomic
    def update_notes(self, *, actor: User, notes: str) -> UserPermissionGroupTemplate | None:
        target = User.objects.get(pk=self.target_user_id)
        assert_can_manage_target(actor, target)
        current = self._active_assignment()
        if current is None:
            return None
        current.notes = notes
        current.updated_by = actor
        current.save(update_fields=["notes", "updated_at", "updated_by"])
        return current

    @transaction.atomic
    def disable_current(self, *, actor: User) -> UserPermissionGroupTemplate | None:
        """
        Soft-disable the current assignment and strip the template's groups from the user
        (the inverse of an additive assignment — leaves manually held groups in place).
        """
        target = User.objects.get(pk=self.target_user_id)
        assert_can_manage_target(actor, target)
        current = self._active_assignment()
        if current is None:
            return None
        assert_actor_may_assign_template(actor, template=current.template)

        previous_template = current.template
        current.is_active = False
        current.updated_by = actor
        current.save(update_fields=["is_active", "updated_at", "updated_by"])

        previous_ids = TemplateRebaseHandler._template_group_ids(previous_template)
        if previous_ids:
            from django.contrib.auth.models import Group
            target.groups.remove(*Group.objects.filter(pk__in=previous_ids))
        return current
