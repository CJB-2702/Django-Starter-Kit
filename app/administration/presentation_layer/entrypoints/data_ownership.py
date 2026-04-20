from django.db.models import Prefetch
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from app.administration.models import Organization, OwnershipGroup
from app.administration.presentation_layer.search.reference_scope import (
    list_divisions,
    list_organizations,
    list_ownership_groups,
)


@require_http_methods(["GET"])
def data_ownership_index(request: HttpRequest) -> HttpResponse:
    """Browse divisions, organizations, and ownership groups; open a portal from each row."""
    actor = request.user
    divisions = list_divisions(actor).prefetch_related(
        Prefetch(
            "organizations",
            queryset=Organization.objects.order_by("name"),
        ),
    )
    organizations = list_organizations(actor).prefetch_related(
        Prefetch(
            "ownership_groups",
            queryset=OwnershipGroup.objects.order_by("name"),
        ),
    )
    ownership_groups = list_ownership_groups(actor)
    return render(
        request,
        "data_ownership/index.html",
        {
            "divisions": divisions,
            "organizations": organizations,
            "ownership_groups": ownership_groups,
        },
    )
