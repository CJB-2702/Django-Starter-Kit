from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import transaction

from app.administration.control_layer.data_ownership.domain_assignment_policy_guard import (
    assert_actor_may_assign_domains,
)
from app.administration.control_layer.data_ownership.template_domain_rebase_handler import (
    TemplateDomainRebaseHandler,
)
from app.administration.models import Domain, DomainTemplate, UserDomain, UserDomainTemplate

User = get_user_model()


class UserDomainAssignmentContext:
    """Control entry for a user's active domain template and explicit domain assignments."""

    def __init__(self, target_user_id: int) -> None:
        self.target_user_id = target_user_id

    def _active_template_assignment(self) -> UserDomainTemplate | None:
        try:
            return UserDomainTemplate.objects.select_related("template").get(
                user_id=self.target_user_id,
                is_active=True,
            )
        except UserDomainTemplate.DoesNotExist:
            return None

    @transaction.atomic
    def assign_domain_template(
        self,
        *,
        actor: User,
        template_id: int,
        additive: bool = False,
    ) -> UserDomainTemplate:
        target = User.objects.get(pk=self.target_user_id)
        new_template = DomainTemplate.objects.get(pk=template_id)
        if not new_template.is_active:
            from app.administration.control_layer.data_ownership.domain_assignment_policy_guard import (
                DomainAccessDenied,
            )
            raise DomainAccessDenied("Cannot assign an inactive domain template.")

        assert_actor_may_assign_domains(actor, template=new_template)

        previous = self._active_template_assignment()
        previous_template = previous.template if previous is not None else None

        if previous is not None:
            previous.is_active = False
            previous.updated_by = actor
            previous.save(update_fields=["is_active", "updated_at", "updated_by"])

        row = UserDomainTemplate.all_objects.create(
            user=target,
            template=new_template,
            is_active=True,
            created_by=actor,
            updated_by=actor,
        )

        handler = TemplateDomainRebaseHandler(
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
    def re_rebase_current(self, *, actor: User) -> UserDomainTemplate | None:
        """Sync the user's domains to the currently assigned template (no swap)."""
        target = User.objects.get(pk=self.target_user_id)
        current = self._active_template_assignment()
        if current is None:
            return None
        assert_actor_may_assign_domains(actor, template=current.template)
        TemplateDomainRebaseHandler(
            user=target,
            new_template=current.template,
            previous_template=current.template,
        ).rebase()
        return current

    @transaction.atomic
    def disable_current(self, *, actor: User) -> UserDomainTemplate | None:
        """
        Soft-disable the current template assignment and remove its domains from the user
        (inverse of additive assignment — leaves manually assigned domains in place).
        """
        target = User.objects.get(pk=self.target_user_id)
        current = self._active_template_assignment()
        if current is None:
            return None
        assert_actor_may_assign_domains(actor, template=current.template)

        previous_template = current.template
        current.is_active = False
        current.updated_by = actor
        current.save(update_fields=["is_active", "updated_at", "updated_by"])

        previous_ids = TemplateDomainRebaseHandler._template_domain_ids(previous_template)
        if previous_ids:
            UserDomain.objects.filter(
                user=target,
                domain_id__in=previous_ids,
                is_active=True,
            ).update(is_active=False)

        return current

    @transaction.atomic
    def assign_explicit_domain(
        self,
        *,
        actor: User,
        domain_id: int,
    ) -> UserDomain:
        target = User.objects.get(pk=self.target_user_id)
        domain = Domain.objects.get(pk=domain_id)
        assert_actor_may_assign_domains(actor, domains=[domain])

        assignment, _created = UserDomain.objects.get_or_create(
            user=target,
            domain=domain,
            defaults={"is_active": True, "created_by": actor, "updated_by": actor},
        )
        if not _created and not assignment.is_active:
            assignment.is_active = True
            assignment.updated_by = actor
            assignment.save(update_fields=["is_active", "updated_at", "updated_by"])
        return assignment

    @transaction.atomic
    def remove_explicit_domain(self, *, actor: User, domain_id: int) -> None:
        target = User.objects.get(pk=self.target_user_id)
        try:
            assignment = UserDomain.objects.get(
                user=target,
                domain_id=domain_id,
                is_active=True,
            )
            assignment.is_active = False
            assignment.updated_by = actor
            assignment.save(update_fields=["is_active", "updated_at", "updated_by"])
        except UserDomain.DoesNotExist:
            pass
