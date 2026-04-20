from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import transaction

from app.administration.control_layer.permission_grant_policy import (
    assert_actor_may_assign_division,
    assert_actor_may_assign_organization,
    assert_actor_may_assign_ownership_group,
    assert_actor_may_disable_user_division,
    assert_actor_may_disable_user_organization,
    assert_actor_may_disable_user_ownership_group,
    assert_can_manage_target,
)
from app.administration.control_layer.domain_structs.user_ownership_struct import (
    UserOwnershipStruct,
)
from app.administration.models import (
    Division,
    Organization,
    OrganizationOwnershipGroup,
    OwnershipGroup,
    UserDivision,
    UserOrganization,
    UserOwnershipGroup,
)

User = get_user_model()


def _ownership_group_ids_for_org_ids(org_ids: list[int]) -> set[int]:
    if not org_ids:
        return set()
    return set(
        OrganizationOwnershipGroup.objects.filter(organization_id__in=org_ids).values_list(
            "ownership_group_id",
            flat=True,
        ),
    )


class OwnershipContext:
    """Control entry for user ↔ division / organization / ownership group assignments."""

    def __init__(self, target_user_id: int, *, eager: bool = True) -> None:
        self.target_user_id = target_user_id
        self._eager = eager
        self._struct = UserOwnershipStruct.load(target_user_id, eager=eager)

    @classmethod
    def from_struct(cls, struct: UserOwnershipStruct) -> OwnershipContext:
        ctx = cls(struct.user_id, eager=True)
        ctx._struct = struct
        return ctx

    @property
    def struct(self) -> UserOwnershipStruct:
        return self._struct

    def refresh_struct(self) -> None:
        self._struct = UserOwnershipStruct.load(self.target_user_id, eager=self._eager)

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
                disabled=False,
                created_by=actor,
                updated_by=actor,
            )
        else:
            row.disabled = False
            row.updated_by = actor
            row.save(update_fields=["disabled", "updated_at", "updated_by"])
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
        row.disabled = True
        row.updated_by = actor
        row.save(update_fields=["disabled", "updated_at", "updated_by"])
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
                disabled=False,
                created_by=actor,
                updated_by=actor,
            )
        else:
            row.disabled = False
            row.updated_by = actor
            row.save(update_fields=["disabled", "updated_at", "updated_by"])
        self.refresh_struct()
        return row

    @transaction.atomic
    def enable_or_assign_organization_with_ownership_groups(
        self,
        *,
        actor: User,
        organization_id: int,
    ) -> UserOrganization:
        """
        Assign the organization and enable every ownership group linked to it on the M2M.
        Skips groups already assigned (no duplicate rows).
        """
        organization = Organization.objects.prefetch_related("ownership_groups").get(pk=organization_id)
        row = self.enable_or_assign_organization(actor=actor, organization_id=organization_id)
        for og in organization.ownership_groups.all():
            self.enable_or_assign_ownership_group(actor=actor, ownership_group_id=og.pk)
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
        row.disabled = True
        row.updated_by = actor
        row.save(update_fields=["disabled", "updated_at", "updated_by"])
        self.refresh_struct()
        return row

    @transaction.atomic
    def disable_organization_with_ownership_groups(
        self,
        *,
        actor: User,
        organization_id: int,
    ) -> UserOrganization:
        """
        Disable the organization assignment and disable UOG rows for that org’s linked groups,
        except groups still linked to another assigned organization (overlapping org bundles).
        """
        target = User.objects.get(pk=self.target_user_id)
        row = UserOrganization.objects.get(user_id=self.target_user_id, organization_id=organization_id)
        assigned_org_ids = list(
            UserOrganization.objects.filter(user=target).values_list("organization_id", flat=True),
        )
        remaining_org_ids = [oid for oid in assigned_org_ids if oid != organization_id]
        covered_by_other_orgs = _ownership_group_ids_for_org_ids(remaining_org_ids)
        og_ids_from_removed_org = _ownership_group_ids_for_org_ids([organization_id])

        uo = self.disable_organization_assignment(actor=actor, user_organization_id=row.pk)

        for ogid in og_ids_from_removed_org:
            if ogid in covered_by_other_orgs:
                continue
            try:
                uog = UserOwnershipGroup.objects.get(
                    user_id=self.target_user_id,
                    ownership_group_id=ogid,
                )
            except UserOwnershipGroup.DoesNotExist:
                continue
            self.disable_ownership_group_assignment(actor=actor, user_ownership_group_id=uog.pk)
        return uo

    @transaction.atomic
    def enable_or_assign_ownership_group(
        self,
        *,
        actor: User,
        ownership_group_id: int,
    ) -> UserOwnershipGroup:
        target = User.objects.get(pk=self.target_user_id)
        assert_can_manage_target(actor, target)
        ownership_group = OwnershipGroup.objects.get(pk=ownership_group_id)
        assert_actor_may_assign_ownership_group(actor, ownership_group=ownership_group)

        try:
            row = UserOwnershipGroup.all_objects.get(
                user=target,
                ownership_group=ownership_group,
            )
        except UserOwnershipGroup.DoesNotExist:
            row = UserOwnershipGroup.all_objects.create(
                user=target,
                ownership_group=ownership_group,
                disabled=False,
                created_by=actor,
                updated_by=actor,
            )
        else:
            row.disabled = False
            row.updated_by = actor
            row.save(update_fields=["disabled", "updated_at", "updated_by"])
        self.refresh_struct()
        return row

    @transaction.atomic
    def disable_ownership_group_assignment(
        self,
        *,
        actor: User,
        user_ownership_group_id: int,
    ) -> UserOwnershipGroup:
        target = User.objects.get(pk=self.target_user_id)
        assert_can_manage_target(actor, target)
        row = UserOwnershipGroup.all_objects.get(pk=user_ownership_group_id, user=target)
        assert_actor_may_disable_user_ownership_group(actor, row=row)
        row.disabled = True
        row.updated_by = actor
        row.save(update_fields=["disabled", "updated_at", "updated_by"])
        self.refresh_struct()
        return row
