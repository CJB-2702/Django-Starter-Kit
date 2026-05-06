"""Domain ↔ Organization associations: a focused portal for OrganizationDomain links."""

from __future__ import annotations

from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from app.administration.control_layer.permissions.permission_grant_guard import (
    is_admin_actor,
)
from app.administration.models import (
    Domain,
    Organization,
    OrganizationDomain,
)


def _require_admin(request: HttpRequest) -> HttpResponse | None:
    if not is_admin_actor(request.user):
        return HttpResponseForbidden(
            "Only generic_admin or Django superusers may manage domain ↔ organization links.",
        )
    return None


@require_http_methods(["GET", "POST"])
def domain_organizations_portal(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        denied = _require_admin(request)
        if denied is not None:
            return denied
        action = request.POST.get("action", "")
        actor = request.user
        try:
            if action == "link":
                domain_id = int(request.POST.get("domain_id", "0"))
                organization_id = int(request.POST.get("organization_id", "0"))
                if not domain_id or not organization_id:
                    messages.error(request, "Pick both a domain and an organization.")
                else:
                    OrganizationDomain.objects.get_or_create(
                        organization_id=organization_id,
                        domain_id=domain_id,
                        defaults={"created_by": actor, "updated_by": actor},
                    )
                    messages.success(request, "Domain linked to organization.")
            elif action == "unlink":
                link_id = int(request.POST.get("link_id", "0"))
                with transaction.atomic():
                    OrganizationDomain.objects.filter(pk=link_id).delete()
                messages.success(request, "Link removed.")
            else:
                messages.error(request, "Unknown action.")
        except (ObjectDoesNotExist, ValueError) as exc:
            messages.error(request, str(exc))
        return redirect(reverse("domain_organizations_portal"))

    q = request.GET.get("q", "").strip()
    domain_q = request.GET.get("domain_q", "").strip()
    org_q = request.GET.get("org_q", "").strip()

    links_qs = (
        OrganizationDomain.objects.select_related("organization", "domain")
        .order_by("organization__name", "domain__name")
    )
    if q:
        links_qs = links_qs.filter(
            Q(organization__name__icontains=q) | Q(domain__name__icontains=q),
        )

    domains = Domain.objects.order_by("name")
    if domain_q:
        domains = domains.filter(name__icontains=domain_q)

    organizations = Organization.objects.order_by("name")
    if org_q:
        organizations = organizations.filter(name__icontains=org_q)

    return render(
        request,
        "data_access/domain_organizations/portal.html",
        {
            "links": links_qs,
            "domains": domains,
            "organizations": organizations,
            "q": q,
            "domain_q": domain_q,
            "org_q": org_q,
            "can_edit": is_admin_actor(request.user),
        },
    )
