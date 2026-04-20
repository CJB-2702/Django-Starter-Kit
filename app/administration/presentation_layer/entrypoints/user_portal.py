from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from app.administration.control_layer.django_permissions_context import (
    DjangoPermissionsContext,
)
from app.administration.control_layer.ownership_context import OwnershipContext
from app.administration.control_layer.permission_grant_policy import (
    GrantPermissionDenied,
    is_admin_actor,
)
from app.administration.models import (
    Division,
    Organization,
    OwnershipGroup,
    UserDivision,
    UserOrganization,
    UserOwnershipGroup,
)
from app.administration.presentation_layer.search.user_access import (
    load_user_django_permissions_struct,
    load_user_ownership_struct,
)
from app.administration.presentation_layer.search.users import list_users_ordered

User = get_user_model()

CHECK_DIRECT_PERMS_GROUP_NOTICE = (
    "Some selected permissions may be automatically inherited by the user based off of "
    "assigned groups, refer to the below list before committing"
)


def _parse_id_list(post, key: str) -> list[int]:
    out: list[int] = []
    for raw in post.getlist(key):
        try:
            out.append(int(raw))
        except ValueError:
            continue
    return out


@require_http_methods(["GET"])
def user_portal_index(request: HttpRequest) -> HttpResponse:
    query = request.GET.get("q", "").strip()
    active_filter = request.GET.get("active", "all")
    staff_filter = request.GET.get("staff", "all")
    page_size = 25

    users = list_users_ordered()
    if query:
        users = users.filter(username__icontains=query)
    if active_filter in {"yes", "no"}:
        users = users.filter(is_active=(active_filter == "yes"))
    if staff_filter in {"yes", "no"}:
        users = users.filter(is_staff=(staff_filter == "yes"))

    total_count = users.count()
    try:
        page = max(int(request.GET.get("page", "1")), 1)
    except ValueError:
        page = 1
    max_page = max(((total_count - 1) // page_size) + 1, 1)
    page = min(page, max_page)
    offset = (page - 1) * page_size
    users = users[offset : offset + page_size]

    base_context = {
        "users": users,
        "query": query,
        "active_filter": active_filter,
        "staff_filter": staff_filter,
        "total_count": total_count,
        "page": page,
        "max_page": max_page,
        "page_size": page_size,
    }

    return render(
        request,
        "user_portal/index.html",
        base_context,
    )


@require_http_methods(["GET"])
def user_portal_detail(request: HttpRequest, user_id: int) -> HttpResponse:
    """Read-only summary of identity, Django permissions, and organizational scope."""
    target = get_object_or_404(
        User.objects.only(
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "is_active",
            "is_staff",
            "is_superuser",
            "last_login",
            "date_joined",
        ),
        pk=user_id,
    )

    perm_struct = load_user_django_permissions_struct(target.pk)
    ownership = load_user_ownership_struct(target.pk)

    return render(
        request,
        "user_portal/detail.html",
        {
            "target_user": target,
            "perm_struct": perm_struct,
            "ownership": ownership,
            "show_edit_link": is_admin_actor(request.user),
        },
    )


@require_http_methods(["POST"])
def check_direct_permissions_against_group(
    request: HttpRequest,
    user_id: int,
) -> HttpResponse:
    """
    HTML fragment (HTMX): POST ``permission_ids`` from the available-permissions
    multiselect; returns which selected permissions are already granted via the
    user's Django groups, for display under that list.
    """
    if not is_admin_actor(request.user):
        return HttpResponseForbidden("Forbidden")

    target = get_object_or_404(User.objects.only("pk"), pk=user_id)
    permission_ids = _parse_id_list(request.POST, "permission_ids")

    items: list[dict[str, object]] = []
    if permission_ids:
        perms = {
            p.pk: p
            for p in Permission.objects.filter(pk__in=permission_ids).select_related(
                "content_type",
            )
        }
        for pid in permission_ids:
            p = perms.get(pid)
            if p is None:
                continue
            group_names = list(
                target.groups.filter(permissions__id=pid)
                .order_by("name")
                .values_list("name", flat=True)
                .distinct(),
            )
            if not group_names:
                continue
            label = f"{p.content_type.app_label} | {p.content_type.model} | {p.name}"
            items.append(
                {
                    "label": label,
                    "groups": group_names,
                },
            )

    return render(
        request,
        "user_portal/_direct_perm_group_check.html",
        {
            "message": CHECK_DIRECT_PERMS_GROUP_NOTICE,
            "items": items,
        },
    )


@require_http_methods(["GET", "POST"])
def user_portal_edit(request: HttpRequest, user_id: int) -> HttpResponse:
    """
    Restricted editor: password, Django groups/permissions, ownership.

    GET returns 403 unless `is_admin_actor` (Django superuser or `generic_admin` group).
    POST mutations use DjangoPermissionsContext / OwnershipContext; `is_grant_actor` includes
    superusers so those mutations succeed. Grant policy still blocks self-target for grants.
    Password change does not use assert_can_manage_target and may target any user including self.
    """
    if not is_admin_actor(request.user):
        return HttpResponseForbidden(
            "Only Django superusers or members of the generic_admin group may access this page.",
        )

    target = get_object_or_404(
        User.objects.prefetch_related("groups", "user_permissions__content_type"),
        pk=user_id,
    )

    if request.method == "POST":
        action = request.POST.get("action", "")
        try:
            if action == "set_password":
                form = SetPasswordForm(user=target, data=request.POST)
                if form.is_valid():
                    form.save()
                    messages.success(request, "Password updated.")
                    return redirect(reverse("user_portal_edit", kwargs={"user_id": user_id}))
                messages.error(request, "Correct the errors below.")
                return _render_user_portal_edit(
                    request,
                    target,
                    password_form=form,
                )

            ctx_perm = DjangoPermissionsContext(user_id)
            ctx_own = OwnershipContext(user_id)

            if action == "add_groups":
                ids = _parse_id_list(request.POST, "group_ids")
                if not ids:
                    messages.error(request, "Select at least one group to add.")
                else:
                    try:
                        with transaction.atomic():
                            for gid in ids:
                                ctx_perm.add_group(actor=request.user, group_id=gid)
                        messages.success(request, "Group membership updated.")
                    except GrantPermissionDenied as exc:
                        messages.error(request, str(exc))
                return redirect(reverse("user_portal_edit", kwargs={"user_id": user_id}))

            if action == "remove_groups":
                ids = _parse_id_list(request.POST, "group_ids")
                if not ids:
                    messages.error(request, "Select at least one group to remove.")
                else:
                    try:
                        with transaction.atomic():
                            for gid in ids:
                                ctx_perm.remove_group(actor=request.user, group_id=gid)
                        messages.success(request, "Group membership updated.")
                    except GrantPermissionDenied as exc:
                        messages.error(request, str(exc))
                return redirect(reverse("user_portal_edit", kwargs={"user_id": user_id}))

            if action == "add_permissions":
                ids = _parse_id_list(request.POST, "permission_ids")
                if not ids:
                    messages.error(request, "Select at least one permission to add.")
                else:
                    try:
                        with transaction.atomic():
                            for pid in ids:
                                ctx_perm.add_direct_permission(
                                    actor=request.user,
                                    permission_id=pid,
                                )
                        messages.success(request, "Direct permissions updated.")
                    except GrantPermissionDenied as exc:
                        messages.error(request, str(exc))
                return redirect(reverse("user_portal_edit", kwargs={"user_id": user_id}))

            if action == "remove_permissions":
                ids = _parse_id_list(request.POST, "permission_ids")
                if not ids:
                    messages.error(request, "Select at least one permission to remove.")
                else:
                    try:
                        with transaction.atomic():
                            for pid in ids:
                                ctx_perm.remove_direct_permission(
                                    actor=request.user,
                                    permission_id=pid,
                                )
                        messages.success(request, "Direct permissions updated.")
                    except GrantPermissionDenied as exc:
                        messages.error(request, str(exc))
                return redirect(reverse("user_portal_edit", kwargs={"user_id": user_id}))

            if action == "assign_divisions":
                ids = _parse_id_list(request.POST, "division_ids")
                if not ids:
                    messages.error(request, "Select at least one division to assign.")
                else:
                    try:
                        with transaction.atomic():
                            for did in ids:
                                ctx_own.enable_or_assign_division(
                                    actor=request.user,
                                    division_id=did,
                                )
                        messages.success(request, "Division assignment updated.")
                    except GrantPermissionDenied as exc:
                        messages.error(request, str(exc))
                return redirect(reverse("user_portal_edit", kwargs={"user_id": user_id}))

            if action == "disable_divisions":
                ids = _parse_id_list(request.POST, "division_ids")
                if not ids:
                    messages.error(request, "Select at least one division to remove.")
                else:
                    try:
                        with transaction.atomic():
                            for did in ids:
                                row = UserDivision.objects.get(user_id=user_id, division_id=did)
                                ctx_own.disable_division_assignment(
                                    actor=request.user,
                                    user_division_id=row.pk,
                                )
                        messages.success(request, "Division assignment updated.")
                    except ObjectDoesNotExist:
                        messages.error(request, "That division assignment was not found.")
                    except GrantPermissionDenied as exc:
                        messages.error(request, str(exc))
                return redirect(reverse("user_portal_edit", kwargs={"user_id": user_id}))

            if action == "assign_organizations":
                ids = _parse_id_list(request.POST, "organization_ids")
                if not ids:
                    messages.error(request, "Select at least one organization to assign.")
                else:
                    try:
                        with transaction.atomic():
                            for oid in ids:
                                ctx_own.enable_or_assign_organization(
                                    actor=request.user,
                                    organization_id=oid,
                                )
                        messages.success(request, "Organization assignment updated.")
                    except GrantPermissionDenied as exc:
                        messages.error(request, str(exc))
                return redirect(reverse("user_portal_edit", kwargs={"user_id": user_id}))

            if action == "assign_organization_with_groups":
                ids = _parse_id_list(request.POST, "organization_ids")
                if not ids:
                    messages.error(request, "Select an organization to assign.")
                else:
                    try:
                        with transaction.atomic():
                            for oid in ids:
                                ctx_own.enable_or_assign_organization_with_ownership_groups(
                                    actor=request.user,
                                    organization_id=oid,
                                )
                        messages.success(request, "Organization and linked ownership groups updated.")
                    except GrantPermissionDenied as exc:
                        messages.error(request, str(exc))
                return redirect(reverse("user_portal_edit", kwargs={"user_id": user_id}))

            if action == "disable_organizations":
                ids = _parse_id_list(request.POST, "organization_ids")
                if not ids:
                    messages.error(request, "Select at least one organization to remove.")
                else:
                    try:
                        with transaction.atomic():
                            for oid in ids:
                                row = UserOrganization.objects.get(
                                    user_id=user_id,
                                    organization_id=oid,
                                )
                                ctx_own.disable_organization_assignment(
                                    actor=request.user,
                                    user_organization_id=row.pk,
                                )
                        messages.success(request, "Organization assignment updated.")
                    except ObjectDoesNotExist:
                        messages.error(request, "That organization assignment was not found.")
                    except GrantPermissionDenied as exc:
                        messages.error(request, str(exc))
                return redirect(reverse("user_portal_edit", kwargs={"user_id": user_id}))

            if action == "disable_organization_with_groups":
                ids = _parse_id_list(request.POST, "organization_ids")
                if not ids:
                    messages.error(request, "Select at least one organization to remove.")
                else:
                    try:
                        with transaction.atomic():
                            for oid in ids:
                                ctx_own.disable_organization_with_ownership_groups(
                                    actor=request.user,
                                    organization_id=oid,
                                )
                        messages.success(request, "Organization and linked ownership groups updated.")
                    except ObjectDoesNotExist:
                        messages.error(request, "That organization assignment was not found.")
                    except GrantPermissionDenied as exc:
                        messages.error(request, str(exc))
                return redirect(reverse("user_portal_edit", kwargs={"user_id": user_id}))

            if action == "assign_ownership_groups":
                ids = _parse_id_list(request.POST, "ownership_group_ids")
                if not ids:
                    messages.error(request, "Select at least one ownership group to assign.")
                else:
                    try:
                        with transaction.atomic():
                            for ogid in ids:
                                ctx_own.enable_or_assign_ownership_group(
                                    actor=request.user,
                                    ownership_group_id=ogid,
                                )
                        messages.success(request, "Ownership group assignment updated.")
                    except GrantPermissionDenied as exc:
                        messages.error(request, str(exc))
                return redirect(reverse("user_portal_edit", kwargs={"user_id": user_id}))

            if action == "disable_ownership_groups":
                ids = _parse_id_list(request.POST, "ownership_group_ids")
                if not ids:
                    messages.error(request, "Select at least one ownership group to remove.")
                else:
                    try:
                        with transaction.atomic():
                            for ogid in ids:
                                row = UserOwnershipGroup.objects.get(
                                    user_id=user_id,
                                    ownership_group_id=ogid,
                                )
                                ctx_own.disable_ownership_group_assignment(
                                    actor=request.user,
                                    user_ownership_group_id=row.pk,
                                )
                        messages.success(request, "Ownership group assignment updated.")
                    except ObjectDoesNotExist:
                        messages.error(request, "That ownership group assignment was not found.")
                    except GrantPermissionDenied as exc:
                        messages.error(request, str(exc))
                return redirect(reverse("user_portal_edit", kwargs={"user_id": user_id}))

            messages.error(request, "Unknown action.")
            return redirect(reverse("user_portal_edit", kwargs={"user_id": user_id}))
        except ObjectDoesNotExist:
            messages.error(request, "The selected record was not found.")
            return redirect(reverse("user_portal_edit", kwargs={"user_id": user_id}))

    return _render_user_portal_edit(request, target, password_form=None)


def _render_user_portal_edit(
    request: HttpRequest,
    target: User,
    *,
    password_form: SetPasswordForm | None,
) -> HttpResponse:
    perm_struct = load_user_django_permissions_struct(target.pk)
    ownership = load_user_ownership_struct(target.pk)

    assigned_group_ids = target.groups.values_list("pk", flat=True)
    groups_available = list(
        Group.objects.exclude(pk__in=assigned_group_ids).order_by("name"),
    )
    groups_assigned = list(target.groups.order_by("name"))

    direct_ids = target.user_permissions.values_list("pk", flat=True)
    permissions_available = list(
        Permission.objects.select_related("content_type")
        .exclude(pk__in=direct_ids)
        .order_by(
            "content_type__app_label",
            "content_type__model",
            "codename",
        ),
    )
    permissions_assigned = list(
        target.user_permissions.select_related("content_type").order_by(
            "content_type__app_label",
            "content_type__model",
            "codename",
        ),
    )

    available_perm_ids = {p.pk for p in permissions_available}
    group_granted_perm_ids = set(
        Permission.objects.filter(group__user=target)
        .values_list("pk", flat=True)
        .distinct(),
    )
    inherited_permission_ids = sorted(available_perm_ids & group_granted_perm_ids)

    assigned_division_ids = [d.pk for d in ownership.divisions]
    divisions_available = list(
        Division.objects.exclude(pk__in=assigned_division_ids).order_by("name"),
    )
    divisions_assigned = ownership.divisions

    assigned_org_ids = [o.pk for o in ownership.organizations]
    organizations_available = list(
        Organization.objects.exclude(pk__in=assigned_org_ids)
        .order_by("divisions__name", "name")
        .prefetch_related("divisions"),
    )
    organizations_assigned = ownership.organizations

    assigned_og_ids = [g.pk for g in ownership.ownership_groups]
    ownership_groups_available = list(
        OwnershipGroup.objects.exclude(pk__in=assigned_og_ids).order_by("name"),
    )
    ownership_groups_assigned = ownership.ownership_groups

    pwd_form = password_form if password_form is not None else SetPasswordForm(user=target)

    return render(
        request,
        "user_portal/edit.html",
        {
            "target_user": target,
            "perm_struct": perm_struct,
            "ownership": ownership,
            "password_form": pwd_form,
            "groups_available": groups_available,
            "groups_assigned": groups_assigned,
            "permissions_available": permissions_available,
            "permissions_assigned": permissions_assigned,
            "divisions_available": divisions_available,
            "divisions_assigned": divisions_assigned,
            "organizations_available": organizations_available,
            "organizations_assigned": organizations_assigned,
            "ownership_groups_available": ownership_groups_available,
            "ownership_groups_assigned": ownership_groups_assigned,
            "inherited_permission_ids": inherited_permission_ids,
        },
    )
