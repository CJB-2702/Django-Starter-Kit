from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from app.administration.control_layer.division_structure import (
    link_organization_to_division,
    unlink_organization_from_division,
)
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

OG_PORTAL_CHUNK = 32


def _ownership_group_portal_offset(request: HttpRequest, key: str) -> int:
    raw = request.GET.get(key, "0").strip()
    if not raw.isdigit():
        return 0
    return max(0, int(raw))


def _parse_id_list(post, key: str) -> list[int]:
    out: list[int] = []
    for raw in post.getlist(key):
        try:
            out.append(int(raw))
        except ValueError:
            continue
    return out


def _require_grant(request: HttpRequest) -> HttpResponse | None:
    if not is_grant_actor(request.user):
        return HttpResponseForbidden(
            "Only generic_manager, generic_admin, or superusers may change scope assignments.",
        )
    return None


@require_http_methods(["GET", "POST"])
def division_portal(request: HttpRequest, division_id: int) -> HttpResponse:
    division = get_object_or_404(list_divisions(request.user), pk=division_id)
    organizations_assigned = division.organizations.order_by("name")
    assigned_org_ids = set(organizations_assigned.values_list("pk", flat=True))
    organizations_available = list(
        list_organizations(request.user).exclude(pk__in=assigned_org_ids).order_by("name"),
    )
    user_rows = (
        UserDivision.objects.filter(division=division)
        .select_related("user")
        .order_by("user__username")
    )
    assigned_user_ids = list(
        UserDivision.objects.filter(division=division).values_list("user_id", flat=True),
    )
    users_available = list(list_users_ordered().exclude(pk__in=assigned_user_ids))
    users_assigned = User.objects.filter(pk__in=assigned_user_ids).order_by("username")

    if request.method == "POST":
        denied = _require_grant(request)
        if denied is not None:
            return denied
        action = request.POST.get("action")
        actor = request.user
        try:
            if action == "add_organizations":
                ids = _parse_id_list(request.POST, "organization_ids")
                if not ids:
                    messages.error(request, "Select at least one organization to assign.")
                else:
                    with transaction.atomic():
                        for oid in ids:
                            link_organization_to_division(
                                actor=actor,
                                organization_id=oid,
                                division_id=division.pk,
                            )
                    messages.success(request, "Organizations linked to this division.")
            elif action == "remove_organizations":
                ids = _parse_id_list(request.POST, "organization_ids")
                if not ids:
                    messages.error(request, "Select at least one organization to remove.")
                else:
                    with transaction.atomic():
                        for oid in ids:
                            unlink_organization_from_division(
                                actor=actor,
                                organization_id=oid,
                                division_id=division.pk,
                            )
                    messages.success(request, "Organizations removed from this division.")
            elif action == "add_users":
                ids = _parse_id_list(request.POST, "user_ids")
                if not ids:
                    messages.error(request, "Select at least one user to add.")
                else:
                    with transaction.atomic():
                        for uid in ids:
                            ctx = OwnershipContext(uid)
                            ctx.enable_or_assign_division(actor=actor, division_id=division.pk)
                    messages.success(request, "Users added to division.")
            elif action == "remove_users":
                ids = _parse_id_list(request.POST, "user_ids")
                if not ids:
                    messages.error(request, "Select at least one user to remove.")
                else:
                    with transaction.atomic():
                        for uid in ids:
                            ud_row = UserDivision.objects.get(user_id=uid, division_id=division.pk)
                            ctx = OwnershipContext(uid)
                            ctx.disable_division_assignment(
                                actor=actor,
                                user_division_id=ud_row.pk,
                            )
                    messages.success(request, "Division assignments disabled for selected users.")
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
            "organizations_assigned": organizations_assigned,
            "organizations_available": organizations_available,
            "user_rows": user_rows,
            "users_available": users_available,
            "users_assigned": users_assigned,
            "can_assign_scope": is_grant_actor(request.user),
        },
    )


@require_http_methods(["GET", "POST"])
def organization_portal(request: HttpRequest, organization_id: int) -> HttpResponse:
    organization = get_object_or_404(list_organizations(request.user), pk=organization_id)
    ownership_groups_assigned = organization.ownership_groups.order_by("name")
    assigned_og_ids = set(ownership_groups_assigned.values_list("pk", flat=True))
    ownership_groups_available = list(
        list_ownership_groups(request.user).exclude(pk__in=assigned_og_ids).order_by("name"),
    )
    user_rows = (
        UserOrganization.objects.filter(organization=organization)
        .select_related("user")
        .order_by("user__username")
    )
    assigned_user_ids = list(
        UserOrganization.objects.filter(organization=organization).values_list("user_id", flat=True),
    )
    users_available = list(list_users_ordered().exclude(pk__in=assigned_user_ids))
    users_assigned = User.objects.filter(pk__in=assigned_user_ids).order_by("username")

    if request.method == "POST":
        denied = _require_grant(request)
        if denied is not None:
            return denied
        action = request.POST.get("action")
        actor = request.user
        try:
            if action == "add_ownership_groups":
                ids = _parse_id_list(request.POST, "ownership_group_ids")
                if not ids:
                    messages.error(request, "Select at least one ownership group to assign.")
                else:
                    with transaction.atomic():
                        for ogid in ids:
                            from app.administration.models import OrganizationOwnershipGroup
                            OrganizationOwnershipGroup.objects.get_or_create(
                                organization=organization,
                                ownership_group_id=ogid,
                                defaults={"created_by": actor, "updated_by": actor},
                            )
                    messages.success(request, "Ownership groups linked to this organization.")
            elif action == "remove_ownership_groups":
                ids = _parse_id_list(request.POST, "ownership_group_ids")
                if not ids:
                    messages.error(request, "Select at least one ownership group to remove.")
                else:
                    with transaction.atomic():
                        from app.administration.models import OrganizationOwnershipGroup
                        OrganizationOwnershipGroup.objects.filter(
                            organization=organization,
                            ownership_group_id__in=ids,
                        ).delete()
                    messages.success(request, "Ownership groups removed from this organization.")
            elif action == "add_users":
                ids = _parse_id_list(request.POST, "user_ids")
                if not ids:
                    messages.error(request, "Select at least one user to add.")
                else:
                    with transaction.atomic():
                        for uid in ids:
                            ctx = OwnershipContext(uid)
                            ctx.enable_or_assign_organization_with_ownership_groups(
                                actor=actor,
                                organization_id=organization.pk,
                            )
                    messages.success(request, "Users added to organization (and linked ownership groups).")
            elif action == "remove_users":
                ids = _parse_id_list(request.POST, "user_ids")
                if not ids:
                    messages.error(request, "Select at least one user to remove.")
                else:
                    with transaction.atomic():
                        for uid in ids:
                            ctx = OwnershipContext(uid)
                            ctx.disable_organization_with_ownership_groups(
                                actor=actor,
                                organization_id=organization.pk,
                            )
                    messages.success(request, "Organization assignments disabled for selected users.")
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
            "ownership_groups_assigned": ownership_groups_assigned,
            "ownership_groups_available": ownership_groups_available,
            "user_rows": user_rows,
            "users_available": users_available,
            "users_assigned": users_assigned,
            "can_assign_scope": is_grant_actor(request.user),
        },
    )


@require_http_methods(["GET", "POST"])
def ownership_group_portal(request: HttpRequest, ownership_group_id: int) -> HttpResponse:
    ownership_group = get_object_or_404(list_ownership_groups(request.user), pk=ownership_group_id)
    og_portal_htmx_base = reverse(
        "ownership_group_portal",
        kwargs={"ownership_group_id": ownership_group.pk},
    )
    og_org_filter_hx_get = f"{og_portal_htmx_base}?format=htmx-og-organizations-panel"
    og_user_filter_hx_get = f"{og_portal_htmx_base}?format=htmx-og-users-panel"

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

    fmt = request.GET.get("format", "").strip()
    portal_org_q = request.GET.get("portal_org_q", "").strip()
    portal_user_q = request.GET.get("portal_user_q", "").strip()
    can_assign_scope = is_grant_actor(request.user)

    def organizations_qs():
        qs = ownership_group.organizations.order_by("name")
        if portal_org_q:
            qs = qs.filter(name__icontains=portal_org_q)
        return qs

    def user_assignment_qs():
        qs = UserOwnershipGroup.objects.filter(ownership_group=ownership_group).select_related(
            "user",
        )
        if portal_user_q:
            qs = qs.filter(
                Q(user__username__icontains=portal_user_q)
                | Q(user__email__icontains=portal_user_q)
                | Q(user__first_name__icontains=portal_user_q)
                | Q(user__last_name__icontains=portal_user_q),
            )
        return qs.order_by("user__username")

    _og_frag_ctx = {
        "ownership_group": ownership_group,
        "og_portal_htmx_base": og_portal_htmx_base,
        "portal_org_q": portal_org_q,
        "portal_user_q": portal_user_q,
        "og_portal_chunk": OG_PORTAL_CHUNK,
        "can_assign_scope": can_assign_scope,
    }

    if fmt == "htmx-og-organizations-panel":
        oqs = organizations_qs()
        total = oqs.count()
        chunk = list(oqs[:OG_PORTAL_CHUNK])
        next_off = len(chunk)
        return render(
            request,
            "scope/_ownership_group_portal_orgs_panel.html",
            {
                **_og_frag_ctx,
                "og_orgs_chunk": chunk,
                "og_orgs_total": total,
                "og_orgs_next_offset": next_off,
                "og_orgs_has_more": next_off < total,
            },
        )

    if fmt == "htmx-og-organizations-append":
        offset = _ownership_group_portal_offset(request, "org_offset")
        oqs = organizations_qs()
        total = oqs.count()
        chunk = list(oqs[offset : offset + OG_PORTAL_CHUNK])
        next_off = offset + len(chunk)
        return render(
            request,
            "scope/_ownership_group_portal_orgs_append.html",
            {
                **_og_frag_ctx,
                "og_orgs_chunk": chunk,
                "og_orgs_total": total,
                "og_orgs_next_offset": next_off,
                "og_orgs_has_more": next_off < total,
            },
        )

    if fmt == "htmx-og-users-panel":
        uqs = user_assignment_qs()
        total = uqs.count()
        chunk = list(uqs[:OG_PORTAL_CHUNK])
        next_off = len(chunk)
        return render(
            request,
            "scope/_ownership_group_portal_users_panel.html",
            {
                **_og_frag_ctx,
                "og_users_chunk": chunk,
                "og_users_total": total,
                "og_users_next_offset": next_off,
                "og_users_has_more": next_off < total,
            },
        )

    if fmt == "htmx-og-users-append":
        offset = _ownership_group_portal_offset(request, "user_offset")
        uqs = user_assignment_qs()
        total = uqs.count()
        chunk = list(uqs[offset : offset + OG_PORTAL_CHUNK])
        next_off = offset + len(chunk)
        return render(
            request,
            "scope/_ownership_group_portal_users_append.html",
            {
                **_og_frag_ctx,
                "og_users_chunk": chunk,
                "og_users_total": total,
                "og_users_next_offset": next_off,
                "og_users_has_more": next_off < total,
            },
        )

    oqs_full = organizations_qs()
    og_orgs_total = oqs_full.count()
    og_orgs_chunk = list(oqs_full[:OG_PORTAL_CHUNK])
    og_orgs_next_offset = len(og_orgs_chunk)
    og_orgs_has_more = og_orgs_next_offset < og_orgs_total

    uqs_full = user_assignment_qs()
    og_users_total = uqs_full.count()
    og_users_chunk = list(uqs_full[:OG_PORTAL_CHUNK])
    og_users_next_offset = len(og_users_chunk)
    og_users_has_more = og_users_next_offset < og_users_total

    users = list_users_ordered()

    return render(
        request,
        "scope/ownership_group_portal.html",
        {
            "ownership_group": ownership_group,
            "og_portal_htmx_base": og_portal_htmx_base,
            "og_org_filter_hx_get": og_org_filter_hx_get,
            "og_user_filter_hx_get": og_user_filter_hx_get,
            "portal_org_q": portal_org_q,
            "portal_user_q": portal_user_q,
            "og_orgs_chunk": og_orgs_chunk,
            "og_orgs_total": og_orgs_total,
            "og_orgs_next_offset": og_orgs_next_offset,
            "og_orgs_has_more": og_orgs_has_more,
            "og_users_chunk": og_users_chunk,
            "og_users_total": og_users_total,
            "og_users_next_offset": og_users_next_offset,
            "og_users_has_more": og_users_has_more,
            "og_portal_chunk": OG_PORTAL_CHUNK,
            "users": users,
            "can_assign_scope": can_assign_scope,
        },
    )
