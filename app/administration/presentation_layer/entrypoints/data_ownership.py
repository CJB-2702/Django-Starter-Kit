from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from app.administration.presentation_layer.search.data_ownership_index_search import (
    divisions_for_index,
    organizations_for_index,
    ownership_groups_for_index,
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
    ownership_group_q = request.GET.get("ownership_group_q", "").strip()

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

    og_qs = ownership_groups_for_index(actor, search=ownership_group_q)
    og_total = og_qs.count()
    ownership_groups = list(og_qs[:DATA_OWNERSHIP_CHUNK])
    og_next_offset = len(ownership_groups)
    og_has_more = og_next_offset < og_total

    return {
        "division_q": division_q,
        "organization_q": organization_q,
        "ownership_group_q": ownership_group_q,
        "divisions": divisions,
        "divisions_total": div_total,
        "divisions_next_offset": div_next_offset,
        "divisions_has_more": div_has_more,
        "organizations": organizations,
        "organizations_total": org_total,
        "organizations_next_offset": org_next_offset,
        "organizations_has_more": org_has_more,
        "ownership_groups": ownership_groups,
        "ownership_groups_total": og_total,
        "ownership_groups_next_offset": og_next_offset,
        "ownership_groups_has_more": og_has_more,
        "data_ownership_chunk": DATA_OWNERSHIP_CHUNK,
    }


@require_http_methods(["GET"])
def data_ownership_index(request: HttpRequest) -> HttpResponse:
    actor = request.user
    fmt = request.GET.get("format", "").strip()
    division_q = request.GET.get("division_q", "").strip()
    organization_q = request.GET.get("organization_q", "").strip()
    ownership_group_q = request.GET.get("ownership_group_q", "").strip()

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

    if fmt == "htmx-data-ownership-groups-panel":
        og_qs = ownership_groups_for_index(actor, search=ownership_group_q)
        og_total = og_qs.count()
        ownership_groups = list(og_qs[:DATA_OWNERSHIP_CHUNK])
        next_offset = len(ownership_groups)
        return render(
            request,
            "data_ownership/_data_ownership_groups_panel.html",
            {
                "ownership_group_q": ownership_group_q,
                "ownership_groups": ownership_groups,
                "ownership_groups_total": og_total,
                "ownership_groups_next_offset": next_offset,
                "ownership_groups_has_more": next_offset < og_total,
                "data_ownership_chunk": DATA_OWNERSHIP_CHUNK,
            },
        )

    if fmt == "htmx-data-ownership-groups-append":
        offset = _non_negative_offset(request)
        og_qs = ownership_groups_for_index(actor, search=ownership_group_q)
        og_total = og_qs.count()
        ownership_groups = list(og_qs[offset : offset + DATA_OWNERSHIP_CHUNK])
        next_offset = offset + len(ownership_groups)
        return render(
            request,
            "data_ownership/_data_ownership_groups_append.html",
            {
                "ownership_group_q": ownership_group_q,
                "ownership_groups": ownership_groups,
                "ownership_groups_total": og_total,
                "ownership_groups_next_offset": next_offset,
                "ownership_groups_has_more": next_offset < og_total,
                "data_ownership_chunk": DATA_OWNERSHIP_CHUNK,
            },
        )

    return render(
        request,
        "data_ownership/index.html",
        _data_ownership_index_context(request),
    )
