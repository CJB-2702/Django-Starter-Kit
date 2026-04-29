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

from app.administration.control_layer.data_ownership.data_ownership_context import (
    DataOwnershipContext,
)
from app.administration.control_layer.data_ownership.division_structure import (
    link_organization_to_division,
    unlink_organization_from_division,
)
from app.administration.control_layer.permissions.permission_grant_guard import (
    GrantPermissionDenied,
    is_grant_actor,
)
from app.administration.models import UserDivision, UserDomain, UserOrganization
from app.administration.presentation_layer.search.reference_scope import (
    list_divisions,
    list_domains,
    list_organizations,
)
from app.administration.presentation_layer.search.users import list_users_ordered

User = get_user_model()

DOMAIN_PORTAL_CHUNK = 32


def _domain_portal_offset(request: HttpRequest, key: str) -> int:
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
                            ctx = DataOwnershipContext(uid)
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
                            ctx = DataOwnershipContext(uid)
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
    domains_assigned = organization.domains.order_by("name")
    assigned_domain_ids = set(domains_assigned.values_list("pk", flat=True))
    domains_available = list(
        list_domains(request.user).exclude(pk__in=assigned_domain_ids).order_by("name"),
    )
    user_rows = (
        UserOrganization.objects.filter(organization=organization)
        .select_related("user")
        .order_by("user__username")
    )
    assigned_user_ids = list(
        UserOrganization.objects.filter(organization=organization).values_list(
            "user_id",
            flat=True,
        ),
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
            if action == "add_domains":
                ids = _parse_id_list(request.POST, "domain_ids")
                if not ids:
                    messages.error(request, "Select at least one data domain to assign.")
                else:
                    with transaction.atomic():
                        for did in ids:
                            from app.administration.models import OrganizationDomain
                            OrganizationDomain.objects.get_or_create(
                                organization=organization,
                                domain_id=did,
                                defaults={"created_by": actor, "updated_by": actor},
                            )
                    messages.success(request, "Data domains linked to this organization.")
            elif action == "remove_domains":
                ids = _parse_id_list(request.POST, "domain_ids")
                if not ids:
                    messages.error(request, "Select at least one data domain to remove.")
                else:
                    with transaction.atomic():
                        from app.administration.models import OrganizationDomain
                        OrganizationDomain.objects.filter(
                            organization=organization,
                            domain_id__in=ids,
                        ).delete()
                    messages.success(request, "Data domains removed from this organization.")
            elif action == "add_users":
                ids = _parse_id_list(request.POST, "user_ids")
                if not ids:
                    messages.error(request, "Select at least one user to add.")
                else:
                    with transaction.atomic():
                        for uid in ids:
                            ctx = DataOwnershipContext(uid)
                            ctx.enable_or_assign_organization_with_domains(
                                actor=actor,
                                organization_id=organization.pk,
                            )
                    messages.success(
                        request,
                        "Users added to organization (and linked data domains).",
                    )
            elif action == "remove_users":
                ids = _parse_id_list(request.POST, "user_ids")
                if not ids:
                    messages.error(request, "Select at least one user to remove.")
                else:
                    with transaction.atomic():
                        for uid in ids:
                            ctx = DataOwnershipContext(uid)
                            ctx.disable_organization_with_domains(
                                actor=actor,
                                organization_id=organization.pk,
                            )
                    messages.success(
                        request,
                        "Organization assignments disabled for selected users.",
                    )
            else:
                messages.error(request, "Unknown action.")
        except GrantPermissionDenied as exc:
            messages.error(request, str(exc))
        except (ObjectDoesNotExist, ValueError) as exc:
            messages.error(request, str(exc))
        return redirect(
            reverse("organization_portal", kwargs={"organization_id": organization.pk}),
        )

    return render(
        request,
        "scope/organization_portal.html",
        {
            "organization": organization,
            "domains_assigned": domains_assigned,
            "domains_available": domains_available,
            "user_rows": user_rows,
            "users_available": users_available,
            "users_assigned": users_assigned,
            "can_assign_scope": is_grant_actor(request.user),
        },
    )


@require_http_methods(["GET", "POST"])
def domain_portal(request: HttpRequest, domain_id: int) -> HttpResponse:
    domain = get_object_or_404(list_domains(request.user), pk=domain_id)
    domain_portal_htmx_base = reverse("domain_portal", kwargs={"domain_id": domain.pk})
    domain_org_filter_hx_get = f"{domain_portal_htmx_base}?format=htmx-domain-organizations-panel"
    domain_user_filter_hx_get = f"{domain_portal_htmx_base}?format=htmx-domain-users-panel"

    if request.method == "POST":
        denied = _require_grant(request)
        if denied is not None:
            return denied
        action = request.POST.get("action")
        actor = request.user
        try:
            if action == "assign_user":
                tid = int(request.POST.get("target_user_id", "0"))
                ctx = DataOwnershipContext(tid)
                ctx.enable_or_assign_domain(actor=actor, domain_id=domain.pk)
                messages.success(request, "User added to data domain.")
            elif action == "disable_assignment":
                ud_pk = int(request.POST.get("user_domain_id", "0"))
                ud_row = UserDomain.objects.get(pk=ud_pk)
                if ud_row.domain_id != domain.pk:
                    messages.error(request, "Invalid assignment.")
                else:
                    ctx = DataOwnershipContext(ud_row.user_id)
                    ctx.disable_domain_assignment(actor=actor, user_domain_id=ud_pk)
                    messages.success(request, "Data domain assignment disabled.")
            else:
                messages.error(request, "Unknown action.")
        except GrantPermissionDenied as exc:
            messages.error(request, str(exc))
        except (ObjectDoesNotExist, ValueError) as exc:
            messages.error(request, str(exc))
        return redirect(reverse("domain_portal", kwargs={"domain_id": domain.pk}))

    fmt = request.GET.get("format", "").strip()
    portal_org_q = request.GET.get("portal_org_q", "").strip()
    portal_user_q = request.GET.get("portal_user_q", "").strip()
    can_assign_scope = is_grant_actor(request.user)

    def organizations_qs():
        qs = domain.organizations.order_by("name")
        if portal_org_q:
            qs = qs.filter(name__icontains=portal_org_q)
        return qs

    def user_assignment_qs():
        qs = UserDomain.objects.filter(domain=domain).select_related("user")
        if portal_user_q:
            qs = qs.filter(
                Q(user__username__icontains=portal_user_q)
                | Q(user__email__icontains=portal_user_q)
                | Q(user__first_name__icontains=portal_user_q)
                | Q(user__last_name__icontains=portal_user_q),
            )
        return qs.order_by("user__username")

    _domain_frag_ctx = {
        "domain": domain,
        "domain_portal_htmx_base": domain_portal_htmx_base,
        "portal_org_q": portal_org_q,
        "portal_user_q": portal_user_q,
        "domain_portal_chunk": DOMAIN_PORTAL_CHUNK,
        "can_assign_scope": can_assign_scope,
    }

    if fmt == "htmx-domain-organizations-panel":
        oqs = organizations_qs()
        total = oqs.count()
        chunk = list(oqs[:DOMAIN_PORTAL_CHUNK])
        next_off = len(chunk)
        return render(
            request,
            "scope/_domain_portal_orgs_panel.html",
            {
                **_domain_frag_ctx,
                "domain_orgs_chunk": chunk,
                "domain_orgs_total": total,
                "domain_orgs_next_offset": next_off,
                "domain_orgs_has_more": next_off < total,
            },
        )

    if fmt == "htmx-domain-organizations-append":
        offset = _domain_portal_offset(request, "org_offset")
        oqs = organizations_qs()
        total = oqs.count()
        chunk = list(oqs[offset : offset + DOMAIN_PORTAL_CHUNK])
        next_off = offset + len(chunk)
        return render(
            request,
            "scope/_domain_portal_orgs_append.html",
            {
                **_domain_frag_ctx,
                "domain_orgs_chunk": chunk,
                "domain_orgs_total": total,
                "domain_orgs_next_offset": next_off,
                "domain_orgs_has_more": next_off < total,
            },
        )

    if fmt == "htmx-domain-users-panel":
        uqs = user_assignment_qs()
        total = uqs.count()
        chunk = list(uqs[:DOMAIN_PORTAL_CHUNK])
        next_off = len(chunk)
        return render(
            request,
            "scope/_domain_portal_users_panel.html",
            {
                **_domain_frag_ctx,
                "domain_users_chunk": chunk,
                "domain_users_total": total,
                "domain_users_next_offset": next_off,
                "domain_users_has_more": next_off < total,
            },
        )

    if fmt == "htmx-domain-users-append":
        offset = _domain_portal_offset(request, "user_offset")
        uqs = user_assignment_qs()
        total = uqs.count()
        chunk = list(uqs[offset : offset + DOMAIN_PORTAL_CHUNK])
        next_off = offset + len(chunk)
        return render(
            request,
            "scope/_domain_portal_users_append.html",
            {
                **_domain_frag_ctx,
                "domain_users_chunk": chunk,
                "domain_users_total": total,
                "domain_users_next_offset": next_off,
                "domain_users_has_more": next_off < total,
            },
        )

    oqs_full = organizations_qs()
    domain_orgs_total = oqs_full.count()
    domain_orgs_chunk = list(oqs_full[:DOMAIN_PORTAL_CHUNK])
    domain_orgs_next_offset = len(domain_orgs_chunk)
    domain_orgs_has_more = domain_orgs_next_offset < domain_orgs_total

    uqs_full = user_assignment_qs()
    domain_users_total = uqs_full.count()
    domain_users_chunk = list(uqs_full[:DOMAIN_PORTAL_CHUNK])
    domain_users_next_offset = len(domain_users_chunk)
    domain_users_has_more = domain_users_next_offset < domain_users_total

    users = list_users_ordered()

    return render(
        request,
        "scope/domain_portal.html",
        {
            "domain": domain,
            "domain_portal_htmx_base": domain_portal_htmx_base,
            "domain_org_filter_hx_get": domain_org_filter_hx_get,
            "domain_user_filter_hx_get": domain_user_filter_hx_get,
            "portal_org_q": portal_org_q,
            "portal_user_q": portal_user_q,
            "domain_orgs_chunk": domain_orgs_chunk,
            "domain_orgs_total": domain_orgs_total,
            "domain_orgs_next_offset": domain_orgs_next_offset,
            "domain_orgs_has_more": domain_orgs_has_more,
            "domain_users_chunk": domain_users_chunk,
            "domain_users_total": domain_users_total,
            "domain_users_next_offset": domain_users_next_offset,
            "domain_users_has_more": domain_users_has_more,
            "domain_portal_chunk": DOMAIN_PORTAL_CHUNK,
            "users": users,
            "can_assign_scope": can_assign_scope,
        },
    )
