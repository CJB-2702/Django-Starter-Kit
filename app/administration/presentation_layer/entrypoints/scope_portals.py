from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from app.administration.control_layer.ownership_context import OwnershipContext
from app.administration.control_layer.permission_grant_policy import (
    GrantPermissionDenied,
    is_grant_actor,
)
from app.administration.models import UserDivision, UserOrganization, UserOwnershipGroup
from app.administration.presentation_layer.search.reference_scope import (
    list_divisions,
    list_organizations,
    list_ownership_groups,
)
from app.administration.presentation_layer.search.users import list_users_ordered

User = get_user_model()


def _require_grant(request: HttpRequest) -> HttpResponse | None:
    if not is_grant_actor(request.user):
        return HttpResponseForbidden(
            "Only generic_manager, generic_admin, or superusers may change scope assignments.",
        )
    return None


@require_http_methods(["GET", "POST"])
def division_portal(request: HttpRequest, division_id: int) -> HttpResponse:
    division = get_object_or_404(list_divisions(request.user), pk=division_id)
    organizations = division.organizations.order_by("name")
    user_rows = (
        UserDivision.objects.filter(division=division)
        .select_related("user")
        .order_by("user__username")
    )
    users = list_users_ordered()

    if request.method == "POST":
        denied = _require_grant(request)
        if denied is not None:
            return denied
        action = request.POST.get("action")
        actor = request.user
        try:
            if action == "assign_user":
                tid = int(request.POST.get("target_user_id", "0"))
                ctx = OwnershipContext(tid)
                ctx.enable_or_assign_division(actor=actor, division_id=division.pk)
                messages.success(request, "User added to division.")
            elif action == "disable_assignment":
                ud_pk = int(request.POST.get("user_division_id", "0"))
                ud_row = UserDivision.objects.get(pk=ud_pk)
                if ud_row.division_id != division.pk:
                    messages.error(request, "Invalid assignment.")
                else:
                    ctx = OwnershipContext(ud_row.user_id)
                    ctx.disable_division_assignment(actor=actor, user_division_id=ud_pk)
                    messages.success(request, "Division assignment disabled.")
            else:
                messages.error(request, "Unknown action.")
        except GrantPermissionDenied as exc:
            messages.error(request, str(exc))
        except (ObjectDoesNotExist, ValueError) as exc:
            messages.error(request, str(exc))
        return redirect(reverse("division_portal", kwargs={"division_id": division.pk}))

    return render(
        request,
        "scope/division_portal.html",
        {
            "division": division,
            "organizations": organizations,
            "user_rows": user_rows,
            "users": users,
            "can_assign_scope": is_grant_actor(request.user),
        },
    )


@require_http_methods(["GET", "POST"])
def organization_portal(request: HttpRequest, organization_id: int) -> HttpResponse:
    organization = get_object_or_404(list_organizations(request.user), pk=organization_id)
    ownership_groups = organization.ownership_groups.order_by("name")
    user_rows = (
        UserOrganization.objects.filter(organization=organization)
        .select_related("user")
        .order_by("user__username")
    )
    users = list_users_ordered()

    if request.method == "POST":
        denied = _require_grant(request)
        if denied is not None:
            return denied
        action = request.POST.get("action")
        actor = request.user
        try:
            if action == "assign_user":
                tid = int(request.POST.get("target_user_id", "0"))
                ctx = OwnershipContext(tid)
                ctx.enable_or_assign_organization_with_ownership_groups(
                    actor=actor,
                    organization_id=organization.pk,
                )
                messages.success(request, "User assigned to organization (and linked ownership groups).")
            elif action == "disable_assignment":
                ud_pk = int(request.POST.get("user_organization_id", "0"))
                row = UserOrganization.objects.get(pk=ud_pk)
                if row.organization_id != organization.pk:
                    messages.error(request, "Invalid assignment.")
                else:
                    ctx = OwnershipContext(row.user_id)
                    ctx.disable_organization_with_ownership_groups(
                        actor=actor,
                        organization_id=organization.pk,
                    )
                    messages.success(request, "Organization assignment disabled.")
            else:
                messages.error(request, "Unknown action.")
        except GrantPermissionDenied as exc:
            messages.error(request, str(exc))
        except (ObjectDoesNotExist, ValueError) as exc:
            messages.error(request, str(exc))
        return redirect(reverse("organization_portal", kwargs={"organization_id": organization.pk}))

    return render(
        request,
        "scope/organization_portal.html",
        {
            "organization": organization,
            "ownership_groups": ownership_groups,
            "user_rows": user_rows,
            "users": users,
            "can_assign_scope": is_grant_actor(request.user),
        },
    )


@require_http_methods(["GET", "POST"])
def ownership_group_portal(request: HttpRequest, ownership_group_id: int) -> HttpResponse:
    ownership_group = get_object_or_404(list_ownership_groups(request.user), pk=ownership_group_id)
    organizations = ownership_group.organizations.order_by("name")
    user_rows = (
        UserOwnershipGroup.objects.filter(ownership_group=ownership_group)
        .select_related("user")
        .order_by("user__username")
    )
    users = list_users_ordered()

    if request.method == "POST":
        denied = _require_grant(request)
        if denied is not None:
            return denied
        action = request.POST.get("action")
        actor = request.user
        try:
            if action == "assign_user":
                tid = int(request.POST.get("target_user_id", "0"))
                ctx = OwnershipContext(tid)
                ctx.enable_or_assign_ownership_group(
                    actor=actor,
                    ownership_group_id=ownership_group.pk,
                )
                messages.success(request, "User added to ownership group.")
            elif action == "disable_assignment":
                uog_pk = int(request.POST.get("user_ownership_group_id", "0"))
                uog_row = UserOwnershipGroup.objects.get(pk=uog_pk)
                if uog_row.ownership_group_id != ownership_group.pk:
                    messages.error(request, "Invalid assignment.")
                else:
                    ctx = OwnershipContext(uog_row.user_id)
                    ctx.disable_ownership_group_assignment(
                        actor=actor,
                        user_ownership_group_id=uog_pk,
                    )
                    messages.success(request, "Ownership group assignment disabled.")
            else:
                messages.error(request, "Unknown action.")
        except GrantPermissionDenied as exc:
            messages.error(request, str(exc))
        except (ObjectDoesNotExist, ValueError) as exc:
            messages.error(request, str(exc))
        return redirect(reverse("ownership_group_portal", kwargs={"ownership_group_id": ownership_group.pk}))

    return render(
        request,
        "scope/ownership_group_portal.html",
        {
            "ownership_group": ownership_group,
            "organizations": organizations,
            "user_rows": user_rows,
            "users": users,
            "can_assign_scope": is_grant_actor(request.user),
        },
    )
