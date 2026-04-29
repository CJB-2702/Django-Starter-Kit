"""
Policy: who may grant or revoke data-ownership assignments (division, organization, domain).

Guard type: **Policy** — authorization gate for data-ownership grant flows.
"""

from __future__ import annotations

from django.contrib.auth.models import User

from app.administration.control_layer.permissions.permission_grant_guard import (
    GrantPermissionDenied,
    is_admin_actor,
    is_manager_actor,
)
from app.administration.models import (
    Division,
    Domain,
    Organization,
    UserDivision,
    UserDomain,
    UserOrganization,
)


def assert_actor_may_assign_division(actor: User, *, division: Division) -> None:
    if is_admin_actor(actor):
        return
    if not is_manager_actor(actor):
        raise GrantPermissionDenied("Only managers or admins may assign divisions.")
    has_active = UserDivision.objects.filter(user=actor, division=division).exists()
    if not has_active:
        raise GrantPermissionDenied("Manager must belong to the division to assign it.")


def assert_actor_may_assign_organization(actor: User, *, organization: Organization) -> None:
    if is_admin_actor(actor):
        return
    if not is_manager_actor(actor):
        raise GrantPermissionDenied("Only managers or admins may assign organizations.")
    has_active = UserOrganization.objects.filter(user=actor, organization=organization).exists()
    if not has_active:
        raise GrantPermissionDenied("Manager must belong to the organization to assign it.")


def assert_actor_may_assign_domain(actor: User, *, domain: Domain) -> None:
    if is_admin_actor(actor):
        return
    if not is_manager_actor(actor):
        raise GrantPermissionDenied("Only managers or admins may assign data domains.")
    has_active = UserDomain.objects.filter(user=actor, domain=domain).exists()
    if not has_active:
        raise GrantPermissionDenied("Manager must belong to the data domain to assign it.")


def assert_actor_may_disable_user_division(actor: User, *, row: UserDivision) -> None:
    assert_actor_may_assign_division(actor, division=row.division)


def assert_actor_may_disable_user_organization(actor: User, *, row: UserOrganization) -> None:
    assert_actor_may_assign_organization(actor, organization=row.organization)


def assert_actor_may_disable_user_domain(actor: User, *, row: UserDomain) -> None:
    assert_actor_may_assign_domain(actor, domain=row.domain)


def assert_actor_may_attach_organization_to_division(
    actor: User,
    *,
    organization: Organization,
    target_division: Division,
) -> None:
    """
    Place (or move) an organization into ``target_division``.

    Admins may always do this. Managers must belong to the target division and,
    when moving from another division, must also belong to the source division.
    """
    assert_actor_may_assign_division(actor, division=target_division)
    current = organization.division
    if current is not None and current.pk != target_division.pk:
        assert_actor_may_assign_division(actor, division=current)


def assert_actor_may_detach_organization_from_division(
    actor: User,
    *,
    organization: Organization,
    division: Division,
) -> None:
    """Remove an organization's membership in ``division`` (org must be linked there)."""
    if organization.division_id != division.pk:
        raise GrantPermissionDenied("That organization is not linked to this division.")
    assert_actor_may_assign_division(actor, division=division)
