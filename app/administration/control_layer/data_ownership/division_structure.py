"""Structural links between divisions and organizations (not user assignments)."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import transaction

from app.administration.control_layer.data_ownership.data_ownership_grant_guard import (
    assert_actor_may_attach_organization_to_division,
    assert_actor_may_detach_organization_from_division,
)
from app.administration.models import Division, DivisionOrganisation, Organization

User = get_user_model()


@transaction.atomic
def link_organization_to_division(
    *,
    actor: User,
    organization_id: int,
    division_id: int,
) -> DivisionOrganisation:
    division = Division.objects.get(pk=division_id)
    organization = Organization.objects.prefetch_related("divisions").get(pk=organization_id)
    assert_actor_may_attach_organization_to_division(
        actor,
        organization=organization,
        target_division=division,
    )
    DivisionOrganisation.objects.filter(organization=organization).delete()
    return DivisionOrganisation.objects.create(
        division=division,
        organization=organization,
        created_by=actor,
        updated_by=actor,
    )


@transaction.atomic
def unlink_organization_from_division(
    *,
    actor: User,
    organization_id: int,
    division_id: int,
) -> None:
    row = DivisionOrganisation.objects.select_related("organization", "division").get(
        organization_id=organization_id,
        division_id=division_id,
    )
    assert_actor_may_detach_organization_from_division(
        actor,
        organization=row.organization,
        division=row.division,
    )
    row.delete()
