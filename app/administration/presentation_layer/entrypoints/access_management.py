from __future__ import annotations

from django.contrib.auth.models import Group, Permission
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from app.administration.constants import DJANGO_GROUPS_UI_NAME
from app.administration.control_layer.permission_grant_policy import is_grant_actor


@require_http_methods(["GET"])
def access_management_index(request: HttpRequest) -> HttpResponse:
    perm_q = request.GET.get("perm_q", "").strip()
    page_size = 32
    groups = Group.objects.order_by("name").all()
    permissions_qs = Permission.objects.select_related("content_type").order_by(
        "content_type__app_label",
        "codename",
    )
    if perm_q:
        permissions_qs = permissions_qs.filter(
            Q(codename__icontains=perm_q)
            | Q(name__icontains=perm_q)
            | Q(content_type__app_label__icontains=perm_q)
            | Q(content_type__model__icontains=perm_q),
        )
    perm_paginator = Paginator(permissions_qs, page_size)
    perm_page = perm_paginator.get_page(request.GET.get("page"))
    permissions = perm_page.object_list
    perm_elided = list(
        perm_paginator.get_elided_page_range(
            perm_page.number,
            on_each_side=1,
            on_ends=1,
        ),
    )

    return render(
        request,
        "access_management/index.html",
        {
            "groups": groups,
            "permissions": permissions,
            "perm_q": perm_q,
            "perm_paginator": perm_paginator,
            "perm_page": perm_page,
            "perm_elided": perm_elided,
            "django_groups_ui_name": DJANGO_GROUPS_UI_NAME,
        },
    )


@require_http_methods(["GET"])
def administration_permissions(request: HttpRequest) -> HttpResponse:
    """
    Canonical permissions collection URL (``/administration/permissions/``).

    Without ``format=htmx-search-results``, browsers are sent to the access management index.
    With that format, returns a flat list of ``<li>`` rows for the ``search-dropdown`` web component
    (see ``HTMX_PATTERNS.md`` §3 and ``ENDPOINT_PATTERNS.md`` §3.6).
    """
    if request.GET.get("format", "").strip() != "htmx-search-results":
        return redirect(reverse("access_management_index"))

    if not is_grant_actor(request.user):
        return HttpResponseForbidden(
            "Only generic_manager, generic_admin, or superusers may search permissions here.",
        )

    qs = Permission.objects.select_related("content_type").order_by(
        "content_type__app_label",
        "codename",
    )

    group_id_raw = request.GET.get("group_id", "").strip()
    if group_id_raw.isdigit():
        group = Group.objects.filter(pk=int(group_id_raw)).first()
        if group is not None:
            qs = qs.exclude(pk__in=group.permissions.values_list("pk", flat=True))

    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(
            Q(codename__icontains=q)
            | Q(name__icontains=q)
            | Q(content_type__app_label__icontains=q)
            | Q(content_type__model__icontains=q),
        )

    page_size = 32
    perm_paginator = Paginator(qs, page_size)
    perm_page = perm_paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "access_management/_permission_search_items.html",
        {"perm_page": perm_page},
    )


@require_http_methods(["GET"])
def access_management_permission_detail(
    request: HttpRequest,
    permission_id: int,
) -> HttpResponse:
    permission = get_object_or_404(
        Permission.objects.select_related("content_type"),
        pk=permission_id,
    )
    groups = (
        Group.objects.filter(permissions=permission)
        .order_by("name")
        .distinct()
    )
    return render(
        request,
        "access_management/permission_detail.html",
        {
            "permission": permission,
            "groups": groups,
            "django_groups_ui_name": DJANGO_GROUPS_UI_NAME,
        },
    )
