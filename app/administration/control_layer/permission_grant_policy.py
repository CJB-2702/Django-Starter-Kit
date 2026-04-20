"""
Policy: who may grant Django groups/permissions and ownership assignments.

Guard type: **Policy** — authorization gate for grant and revoke flows.
"""

from __future__ import annotations

from collections.abc import Iterable

from django.contrib.auth.models import Group, Permission, User

from app.administration.constants import (
    GROUP_GENERIC_ADMIN,
    GROUP_GENERIC_MANAGER,
)
from app.administration.models import (
    Division,
    Organization,
    OwnershipGroup,
    UserDivision,
    UserOrganization,
    UserOwnershipGroup,
)


class GrantPermissionDenied(PermissionError):
    """Raised when the actor is not allowed to perform a grant or revoke action."""


def _is_in_group(user: User, *, group_name: str) -> bool:
    return user.groups.filter(name=group_name).exists()


def is_grant_actor(user: User) -> bool:
    """Return True if the user may use grant flows (superuser, manager, or generic_admin group)."""
    if not user.is_active:
        return False
    if user.is_superuser:
        return True
    return _is_in_group(user, group_name=GROUP_GENERIC_MANAGER) or _is_in_group(
        user,
        group_name=GROUP_GENERIC_ADMIN,
    )


def is_admin_actor(user: User) -> bool:
    """Full portal-admin bypass (same policy checks as ``generic_admin`` group): superuser or that group."""
    if not user.is_active:
        return False
    if user.is_superuser:
        return True
    return _is_in_group(user, group_name=GROUP_GENERIC_ADMIN)


def is_manager_actor(user: User) -> bool:
    return user.is_active and _is_in_group(user, group_name=GROUP_GENERIC_MANAGER)


def assert_can_manage_target(actor: User, target: User) -> None:
    if not is_grant_actor(actor):
        raise GrantPermissionDenied(
            "Only generic_manager, generic_admin, or Django superusers may change grants.",
        )
    if actor.pk == target.pk:
        raise GrantPermissionDenied("Cannot change your own grants through this flow.")


def assert_actor_may_add_permissions(
    actor: User,
    *,
    permissions_to_add: Iterable[Permission],
) -> None:
    if is_admin_actor(actor):
        return
    if not is_manager_actor(actor):
        raise GrantPermissionDenied("Only managers or admins may grant permissions.")
    actor_perm_set = set(actor.get_all_permissions())
    for perm in permissions_to_add:
        key = f"{perm.content_type.app_label}.{perm.codename}"
        if key not in actor_perm_set:
            raise GrantPermissionDenied(
                f"Manager cannot grant permission not held: {key}",
            )


def assert_actor_may_add_groups(actor: User, *, groups_to_add: Iterable[Group]) -> None:
    """Manager may add a group only if every permission in that group is held by the actor."""
    if is_admin_actor(actor):
        return
    if not is_manager_actor(actor):
        raise GrantPermissionDenied("Only managers or admins may grant groups.")
    for group in groups_to_add:
        perms = group.permissions.all()
        assert_actor_may_add_permissions(actor, permissions_to_add=perms)


def assert_actor_may_remove_permissions(
    actor: User,
    *,
    permissions_to_remove: Iterable[Permission],
) -> None:
    """Symmetric rule: removing a permission requires the actor to hold that permission (managers)."""
    assert_actor_may_add_permissions(actor, permissions_to_add=permissions_to_remove)


def assert_actor_may_remove_groups(actor: User, *, groups_to_remove: Iterable[Group]) -> None:
    assert_actor_may_add_groups(actor, groups_to_add=groups_to_remove)


def assert_actor_may_assign_division(actor: User, *, division: Division) -> None:
    if is_admin_actor(actor):
        return
    if not is_manager_actor(actor):
        raise GrantPermissionDenied("Only managers or admins may assign divisions.")

    has_active = UserDivision.objects.filter(
        user=actor,
        division=division,
    ).exists()
    if not has_active:
        raise GrantPermissionDenied(
            "Manager must belong to the division to assign it.",
        )


def assert_actor_may_assign_organization(actor: User, *, organization: Organization) -> None:
    if is_admin_actor(actor):
        return
    if not is_manager_actor(actor):
        raise GrantPermissionDenied("Only managers or admins may assign organizations.")

    has_active = UserOrganization.objects.filter(
        user=actor,
        organization=organization,
    ).exists()
    if not has_active:
        raise GrantPermissionDenied(
            "Manager must belong to the organization to assign it.",
        )


def assert_actor_may_assign_ownership_group(
    actor: User,
    *,
    ownership_group: OwnershipGroup,
) -> None:
    if is_admin_actor(actor):
        return
    if not is_manager_actor(actor):
        raise GrantPermissionDenied("Only managers or admins may assign ownership groups.")

    has_active = UserOwnershipGroup.objects.filter(
        user=actor,
        ownership_group=ownership_group,
    ).exists()
    if not has_active:
        raise GrantPermissionDenied(
            "Manager must belong to the ownership group to assign it.",
        )


def assert_actor_may_disable_user_division(
    actor: User,
    *,
    row: UserDivision,
) -> None:
    assert_actor_may_assign_division(actor, division=row.division)


def assert_actor_may_disable_user_organization(
    actor: User,
    *,
    row: UserOrganization,
) -> None:
    assert_actor_may_assign_organization(actor, organization=row.organization)


def assert_actor_may_disable_user_ownership_group(
    actor: User,
    *,
    row: UserOwnershipGroup,
) -> None:
    assert_actor_may_assign_ownership_group(actor, ownership_group=row.ownership_group)
