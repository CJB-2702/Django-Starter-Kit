from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import transaction

from app.administration.control_layer.data_ownership.data_ownership_grant_guard import (
    assert_actor_may_assign_division,
    assert_actor_may_assign_domain,
    assert_actor_may_assign_organization,
    assert_actor_may_disable_user_division,
    assert_actor_may_disable_user_domain,
    assert_actor_may_disable_user_organization,
)
from app.administration.control_layer.data_ownership.user_data_ownership_struct import (
    UserDataOwnershipStruct,
)
from app.administration.control_layer.permissions.permission_grant_guard import (
    assert_can_manage_target,
)
from app.administration.models import (
    Division,
    Domain,
    Organization,
    OrganizationDomain,
    UserDivision,
    UserDomain,
    UserOrganization,
)

User = get_user_model()


def _domain_ids_for_org_ids(org_ids: list[int]) -> set[int]:
    if not org_ids:
        return set()
    return set(
        OrganizationDomain.objects.filter(organization_id__in=org_ids).values_list(
            "domain_id",
            flat=True,
        ),
    )


class DataOwnershipContext:
    """Control entry for user ↔ division / organization / data domain assignments."""

    def __init__(self, target_user_id: int, *, eager: bool = True) -> None:
        self.target_user_id = target_user_id
        self._eager = eager
        self._struct = UserDataOwnershipStruct.load(target_user_id, eager=eager)

    @classmethod
    def from_struct(cls, struct: UserDataOwnershipStruct) -> DataOwnershipContext:
        ctx = cls(struct.user_id, eager=True)
        ctx._struct = struct
        return ctx

    @property
    def struct(self) -> UserDataOwnershipStruct:
        return self._struct

    def refresh_struct(self) -> None:
        self._struct = UserDataOwnershipStruct.load(self.target_user_id, eager=self._eager)

    @transaction.atomic
    def enable_or_assign_division(
        self,
        *,
        actor: User,
        division_id: int,
    ) -> UserDivision:
        target = User.objects.get(pk=self.target_user_id)
        assert_can_manage_target(actor, target)
        division = Division.objects.get(pk=division_id)
        assert_actor_may_assign_division(actor, division=division)

        try:
            row = UserDivision.all_objects.get(user=target, division=division)
        except UserDivision.DoesNotExist:
            row = UserDivision.all_objects.create(
                user=target,
                division=division,
                is_active=True,
                created_by=actor,
                updated_by=actor,
            )
        else:
            row.is_active = True
            row.updated_by = actor
            row.save(update_fields=["is_active", "updated_at", "updated_by"])
        self.refresh_struct()
        return row

    @transaction.atomic
    def disable_division_assignment(
        self,
        *,
        actor: User,
        user_division_id: int,
    ) -> UserDivision:
        target = User.objects.get(pk=self.target_user_id)
        assert_can_manage_target(actor, target)
        row = UserDivision.all_objects.get(pk=user_division_id, user=target)
        assert_actor_may_disable_user_division(actor, row=row)
        row.is_active = False
        row.updated_by = actor
        row.save(update_fields=["is_active", "updated_at", "updated_by"])
        self.refresh_struct()
        return row

    @transaction.atomic
    def enable_or_assign_organization(
        self,
        *,
        actor: User,
        organization_id: int,
    ) -> UserOrganization:
        target = User.objects.get(pk=self.target_user_id)
        assert_can_manage_target(actor, target)
        organization = Organization.objects.get(pk=organization_id)
        assert_actor_may_assign_organization(actor, organization=organization)

        try:
            row = UserOrganization.all_objects.get(user=target, organization=organization)
        except UserOrganization.DoesNotExist:
            row = UserOrganization.all_objects.create(
                user=target,
                organization=organization,
                is_active=True,
                created_by=actor,
                updated_by=actor,
            )
        else:
            row.is_active = True
            row.updated_by = actor
            row.save(update_fields=["is_active", "updated_at", "updated_by"])
        self.refresh_struct()
        return row

    @transaction.atomic
    def enable_or_assign_organization_with_domains(
        self,
        *,
        actor: User,
        organization_id: int,
    ) -> UserOrganization:
        """
        Assign the organization and enable every data domain linked to it.
        Skips domains already assigned (no duplicate rows).
        """
        organization = Organization.objects.prefetch_related("domains").get(pk=organization_id)
        row = self.enable_or_assign_organization(actor=actor, organization_id=organization_id)
        for d in organization.domains.all():
            self.enable_or_assign_domain(actor=actor, domain_id=d.pk)
        return row

    @transaction.atomic
    def disable_organization_assignment(
        self,
        *,
        actor: User,
        user_organization_id: int,
    ) -> UserOrganization:
        target = User.objects.get(pk=self.target_user_id)
        assert_can_manage_target(actor, target)
        row = UserOrganization.all_objects.get(pk=user_organization_id, user=target)
        assert_actor_may_disable_user_organization(actor, row=row)
        row.is_active = False
        row.updated_by = actor
        row.save(update_fields=["is_active", "updated_at", "updated_by"])
        self.refresh_struct()
        return row

    @transaction.atomic
    def disable_organization_with_domains(
        self,
        *,
        actor: User,
        organization_id: int,
    ) -> UserOrganization:
        """
        Disable the organization assignment and disable UserDomain rows for that
        org's linked domains, except domains still linked to another assigned
        organization (overlapping org bundles).
        """
        target = User.objects.get(pk=self.target_user_id)
        row = UserOrganization.objects.get(
            user_id=self.target_user_id,
            organization_id=organization_id,
        )
        assigned_org_ids = list(
            UserOrganization.objects.filter(user=target).values_list(
                "organization_id",
                flat=True,
            ),
        )
        remaining_org_ids = [oid for oid in assigned_org_ids if oid != organization_id]
        covered_by_other_orgs = _domain_ids_for_org_ids(remaining_org_ids)
        domain_ids_from_removed_org = _domain_ids_for_org_ids([organization_id])

        uo = self.disable_organization_assignment(actor=actor, user_organization_id=row.pk)

        for did in domain_ids_from_removed_org:
            if did in covered_by_other_orgs:
                continue
            try:
                ud = UserDomain.objects.get(user_id=self.target_user_id, domain_id=did)
            except UserDomain.DoesNotExist:
                continue
            self.disable_domain_assignment(actor=actor, user_domain_id=ud.pk)
        return uo

    @transaction.atomic
    def enable_or_assign_domain(
        self,
        *,
        actor: User,
        domain_id: int,
    ) -> UserDomain:
        target = User.objects.get(pk=self.target_user_id)
        assert_can_manage_target(actor, target)
        domain = Domain.objects.get(pk=domain_id)
        assert_actor_may_assign_domain(actor, domain=domain)

        try:
            row = UserDomain.all_objects.get(user=target, domain=domain)
        except UserDomain.DoesNotExist:
            row = UserDomain.all_objects.create(
                user=target,
                domain=domain,
                is_active=True,
                created_by=actor,
                updated_by=actor,
            )
        else:
            row.is_active = True
            row.updated_by = actor
            row.save(update_fields=["is_active", "updated_at", "updated_by"])
        self.refresh_struct()
        return row

    @transaction.atomic
    def disable_domain_assignment(
        self,
        *,
        actor: User,
        user_domain_id: int,
    ) -> UserDomain:
        target = User.objects.get(pk=self.target_user_id)
        assert_can_manage_target(actor, target)
        row = UserDomain.all_objects.get(pk=user_domain_id, user=target)
        assert_actor_may_disable_user_domain(actor, row=row)
        row.is_active = False
        row.updated_by = actor
        row.save(update_fields=["is_active", "updated_at", "updated_by"])
        self.refresh_struct()
        return row
