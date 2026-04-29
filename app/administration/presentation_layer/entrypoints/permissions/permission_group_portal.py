from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from app.administration.constants import DJANGO_GROUP_UI_NAME, DJANGO_GROUPS_UI_NAME
from app.administration.control_layer.permissions.permission_grant_guard import (
    GrantPermissionDenied,
    assert_actor_may_add_groups,
    assert_actor_may_add_permissions,
    assert_actor_may_remove_groups,
    assert_actor_may_remove_permissions,
    assert_can_manage_target,
    is_grant_actor,
)
from app.administration.presentation_layer.search.users import list_users_ordered

User = get_user_model()


def _require_grant(request: HttpRequest) -> HttpResponse | None:
    if not is_grant_actor(request.user):
        return HttpResponseForbidden(
            "Only generic_manager, generic_admin, or superusers may change groups.",
        )
    return None


def _parse_id_list(post, key: str) -> list[int]:
    out: list[int] = []
    for raw in post.getlist(key):
        try:
            out.append(int(raw))
        except ValueError:
            continue
    return out


@require_http_methods(["GET", "POST"])
def permission_group_portal(request: HttpRequest, group_id: int) -> HttpResponse:
    """Manage a single Django ``auth.Group`` (product term: **permission group**)."""
    group = get_object_or_404(
        Group.objects.prefetch_related("permissions__content_type"),
        pk=group_id,
    )

    members = User.objects.filter(groups=group).order_by("username").distinct()
    permissions = group.permissions.select_related("content_type").order_by(
        "content_type__app_label",
        "content_type__model",
        "codename",
    )
    assigned_perm_ids = set(group.permissions.values_list("pk", flat=True))
    permissions_available = list(
        Permission.objects.select_related("content_type")
        .exclude(pk__in=assigned_perm_ids)
        .order_by(
            "content_type__app_label",
            "content_type__model",
            "codename",
        ),
    )
    permissions_assigned = list(permissions)
    users_available = list(list_users_ordered().exclude(groups=group))
    members_list = list(members)

    if request.method == "POST":
        denied = _require_grant(request)
        if denied is not None:
            return denied
        actor = request.user
        action = request.POST.get("action")
        try:
            if action == "add_users":
                ids = _parse_id_list(request.POST, "user_ids")
                if not ids:
                    messages.error(request, "Select at least one user to add.")
                else:
                    with transaction.atomic():
                        for uid in ids:
                            target = User.objects.get(pk=uid)
                            assert_can_manage_target(actor, target)
                            assert_actor_may_add_groups(actor, groups_to_add=[group])
                            target.groups.add(group)
                    messages.success(request, "Users added to group.")
            elif action == "remove_users":
                ids = _parse_id_list(request.POST, "user_ids")
                if not ids:
                    messages.error(request, "Select at least one user to remove.")
                else:
                    with transaction.atomic():
                        for uid in ids:
                            target = User.objects.get(pk=uid)
                            assert_can_manage_target(actor, target)
                            assert_actor_may_remove_groups(actor, groups_to_remove=[group])
                            target.groups.remove(group)
                    messages.success(request, "Users removed from group.")
            elif action == "add_permissions":
                ids = _parse_id_list(request.POST, "permission_ids")
                if not ids:
                    messages.error(request, "Select at least one permission to add.")
                else:
                    with transaction.atomic():
                        for pid in ids:
                            perm = Permission.objects.select_related("content_type").get(pk=pid)
                            assert_actor_may_add_permissions(actor, permissions_to_add=[perm])
                            group.permissions.add(perm)
                    messages.success(request, "Permissions added to group.")
            elif action == "remove_permissions":
                ids = _parse_id_list(request.POST, "permission_ids")
                if not ids:
                    messages.error(request, "Select at least one permission to remove.")
                else:
                    with transaction.atomic():
                        for pid in ids:
                            perm = Permission.objects.select_related("content_type").get(pk=pid)
                            assert_actor_may_remove_permissions(
                                actor,
                                permissions_to_remove=[perm],
                            )
                            group.permissions.remove(perm)
                    messages.success(request, "Permissions removed from group.")
            else:
                messages.error(request, "Unknown action.")
        except GrantPermissionDenied as exc:
            messages.error(request, str(exc))
        except (ObjectDoesNotExist, ValueError) as exc:
            messages.error(request, str(exc))
        return redirect(reverse("permission_group_portal", kwargs={"group_id": group.pk}))

    return render(
        request,
        "access_management/permission_group_portal.html",
        {
            "group": group,
            "members": members,
            "permissions": permissions,
            "users_available": users_available,
            "members_list": members_list,
            "permissions_available": permissions_available,
            "permissions_assigned": permissions_assigned,
            "inherited_permission_ids": [],
            "can_edit": is_grant_actor(request.user),
            "django_group_ui_name": DJANGO_GROUP_UI_NAME,
            "django_groups_ui_name": DJANGO_GROUPS_UI_NAME,
        },
    )
