from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from app.administration.presentation_layer.search.data_ownership_index_search import (
    divisions_for_index,
    domains_for_index,
    organizations_for_index,
)

DATA_OWNERSHIP_CHUNK = 32


def _non_negative_offset(request: HttpRequest) -> int:
    raw = request.GET.get("offset", "0").strip()
    if not raw.isdigit():
        return 0
    return max(0, int(raw))


def _data_ownership_index_context(request: HttpRequest) -> dict:
    actor = request.user
    division_q = request.GET.get("division_q", "").strip()
    organization_q = request.GET.get("organization_q", "").strip()
    domain_q = request.GET.get("domain_q", "").strip()

    div_qs = divisions_for_index(actor, search=division_q)
    div_total = div_qs.count()
    divisions = list(div_qs[:DATA_OWNERSHIP_CHUNK])
    div_next_offset = len(divisions)
    div_has_more = div_next_offset < div_total

    org_qs = organizations_for_index(actor, search=organization_q)
    org_total = org_qs.count()
    organizations = list(org_qs[:DATA_OWNERSHIP_CHUNK])
    org_next_offset = len(organizations)
    org_has_more = org_next_offset < org_total

    dom_qs = domains_for_index(actor, search=domain_q)
    dom_total = dom_qs.count()
    domains = list(dom_qs[:DATA_OWNERSHIP_CHUNK])
    dom_next_offset = len(domains)
    dom_has_more = dom_next_offset < dom_total

    return {
        "division_q": division_q,
        "organization_q": organization_q,
        "domain_q": domain_q,
        "divisions": divisions,
        "divisions_total": div_total,
        "divisions_next_offset": div_next_offset,
        "divisions_has_more": div_has_more,
        "organizations": organizations,
        "organizations_total": org_total,
        "organizations_next_offset": org_next_offset,
        "organizations_has_more": org_has_more,
        "domains": domains,
        "domains_total": dom_total,
        "domains_next_offset": dom_next_offset,
        "domains_has_more": dom_has_more,
        "data_ownership_chunk": DATA_OWNERSHIP_CHUNK,
    }


@require_http_methods(["GET"])
def data_ownership_index(request: HttpRequest) -> HttpResponse:
    actor = request.user
    fmt = request.GET.get("format", "").strip()
    division_q = request.GET.get("division_q", "").strip()
    organization_q = request.GET.get("organization_q", "").strip()
    domain_q = request.GET.get("domain_q", "").strip()

    if fmt == "htmx-data-divisions-panel":
        div_qs = divisions_for_index(actor, search=division_q)
        div_total = div_qs.count()
        divisions = list(div_qs[:DATA_OWNERSHIP_CHUNK])
        next_offset = len(divisions)
        return render(
            request,
            "data_ownership/_data_divisions_panel.html",
            {
                "division_q": division_q,
                "divisions": divisions,
                "divisions_total": div_total,
                "divisions_next_offset": next_offset,
                "divisions_has_more": next_offset < div_total,
                "data_ownership_chunk": DATA_OWNERSHIP_CHUNK,
            },
        )

    if fmt == "htmx-data-divisions-append":
        offset = _non_negative_offset(request)
        div_qs = divisions_for_index(actor, search=division_q)
        div_total = div_qs.count()
        divisions = list(div_qs[offset : offset + DATA_OWNERSHIP_CHUNK])
        next_offset = offset + len(divisions)
        return render(
            request,
            "data_ownership/_data_divisions_append.html",
            {
                "division_q": division_q,
                "divisions": divisions,
                "divisions_total": div_total,
                "divisions_next_offset": next_offset,
                "divisions_has_more": next_offset < div_total,
                "data_ownership_chunk": DATA_OWNERSHIP_CHUNK,
            },
        )

    if fmt == "htmx-data-organizations-panel":
        org_qs = organizations_for_index(actor, search=organization_q)
        org_total = org_qs.count()
        organizations = list(org_qs[:DATA_OWNERSHIP_CHUNK])
        next_offset = len(organizations)
        return render(
            request,
            "data_ownership/_data_organizations_panel.html",
            {
                "organization_q": organization_q,
                "organizations": organizations,
                "organizations_total": org_total,
                "organizations_next_offset": next_offset,
                "organizations_has_more": next_offset < org_total,
                "data_ownership_chunk": DATA_OWNERSHIP_CHUNK,
            },
        )

    if fmt == "htmx-data-organizations-append":
        offset = _non_negative_offset(request)
        org_qs = organizations_for_index(actor, search=organization_q)
        org_total = org_qs.count()
        organizations = list(org_qs[offset : offset + DATA_OWNERSHIP_CHUNK])
        next_offset = offset + len(organizations)
        return render(
            request,
            "data_ownership/_data_organizations_append.html",
            {
                "organization_q": organization_q,
                "organizations": organizations,
                "organizations_total": org_total,
                "organizations_next_offset": next_offset,
                "organizations_has_more": next_offset < org_total,
                "data_ownership_chunk": DATA_OWNERSHIP_CHUNK,
            },
        )

    if fmt == "htmx-data-domains-panel":
        dom_qs = domains_for_index(actor, search=domain_q)
        dom_total = dom_qs.count()
        domains = list(dom_qs[:DATA_OWNERSHIP_CHUNK])
        next_offset = len(domains)
        return render(
            request,
            "data_ownership/_data_domains_panel.html",
            {
                "domain_q": domain_q,
                "domains": domains,
                "domains_total": dom_total,
                "domains_next_offset": next_offset,
                "domains_has_more": next_offset < dom_total,
                "data_ownership_chunk": DATA_OWNERSHIP_CHUNK,
            },
        )

    if fmt == "htmx-data-domains-append":
        offset = _non_negative_offset(request)
        dom_qs = domains_for_index(actor, search=domain_q)
        dom_total = dom_qs.count()
        domains = list(dom_qs[offset : offset + DATA_OWNERSHIP_CHUNK])
        next_offset = offset + len(domains)
        return render(
            request,
            "data_ownership/_data_domains_append.html",
            {
                "domain_q": domain_q,
                "domains": domains,
                "domains_total": dom_total,
                "domains_next_offset": next_offset,
                "domains_has_more": next_offset < dom_total,
                "data_ownership_chunk": DATA_OWNERSHIP_CHUNK,
            },
        )

    return render(
        request,
        "data_ownership/index.html",
        _data_ownership_index_context(request),
    )
