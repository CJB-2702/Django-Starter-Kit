"""Direct querysets for the data-ownership index page."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import CharField, Count, OuterRef, Q, QuerySet, Subquery

from app.administration.control_layer.permissions.permission_grant_guard import is_admin_actor
from app.administration.models import (
    Division,
    DivisionOrganisation,
    Domain,
    Organization,
    UserDivision,
    UserDomain,
    UserOrganization,
)

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser


def _division_id_scope(user: AbstractUser):
    if is_admin_actor(user):
        return None
    return UserDivision.objects.filter(user=user).values_list("division_id", flat=True)


def _organization_id_scope(user: AbstractUser):
    if is_admin_actor(user):
        return None
    return UserOrganization.objects.filter(user=user).values_list(
        "organization_id",
        flat=True,
    )


def _domain_id_scope(user: AbstractUser):
    if is_admin_actor(user):
        return None
    return UserDomain.objects.filter(user=user).values_list("domain_id", flat=True)


def divisions_for_index(user: AbstractUser, *, search: str = "") -> QuerySet[Division]:
    """Divisions visible to ``user``, optional ``name__icontains`` filter, org counts annotated."""
    qs = Division.objects.order_by("name")
    scope = _division_id_scope(user)
    if scope is not None:
        qs = qs.filter(pk__in=scope)
    if search:
        qs = qs.filter(name__icontains=search)
    return qs.annotate(organization_count=Count("organizations", distinct=True))


def organizations_for_index(user: AbstractUser, *, search: str = "") -> QuerySet[Organization]:
    """Organizations visible to ``user`` with domain counts and scoped division name."""
    qs = Organization.objects.all()
    scope = _organization_id_scope(user)
    if scope is not None:
        qs = qs.filter(pk__in=scope)

    if search:
        qs = qs.filter(
            Q(name__icontains=search) | Q(divisions__name__icontains=search),
        ).distinct()

    division_name_sq = (
        DivisionOrganisation.objects.filter(organization_id=OuterRef("pk"))
        .order_by("division__name")
        .values("division__name")[:1]
    )

    return (
        qs.order_by("name")
        .annotate(
            domain_count=Count("domains", distinct=True),
            scoped_division_name=Subquery(division_name_sq, output_field=CharField()),
        )
    )


def domains_for_index(user: AbstractUser, *, search: str = "") -> QuerySet[Domain]:
    """Data domains visible to ``user``, optional ``name__icontains`` filter."""
    qs = Domain.objects.order_by("name")
    scope = _domain_id_scope(user)
    if scope is not None:
        qs = qs.filter(pk__in=scope)
    if search:
        qs = qs.filter(name__icontains=search)
    return qs
