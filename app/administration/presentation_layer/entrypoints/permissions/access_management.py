from __future__ import annotations

from django.contrib.auth.models import Group, Permission
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from app.administration.constants import DJANGO_GROUPS_UI_NAME
from app.administration.control_layer.permissions.permission_grant_guard import is_grant_actor

ACCESS_LIST_CHUNK = 32


def _non_negative_offset(request: HttpRequest) -> int:
    raw = request.GET.get("offset", "0").strip()
    if not raw.isdigit():
        return 0
    return max(0, int(raw))


def _permissions_queryset(perm_q: str):
    qs = Permission.objects.select_related("content_type").order_by(
        "content_type__app_label",
        "codename",
    )
    if perm_q:
        qs = qs.filter(
            Q(codename__icontains=perm_q)
            | Q(name__icontains=perm_q)
            | Q(content_type__app_label__icontains=perm_q)
            | Q(content_type__model__icontains=perm_q),
        )
    return qs


def _groups_queryset(group_q: str):
    qs = Group.objects.order_by("name")
    if group_q:
        qs = qs.filter(name__icontains=group_q)
    return qs


def _access_management_index_context(request: HttpRequest) -> dict:
    group_q = request.GET.get("group_q", "").strip()
    perm_q = request.GET.get("perm_q", "").strip()

    groups_qs = _groups_queryset(group_q)
    groups_total = groups_qs.count()
    groups = list(groups_qs[:ACCESS_LIST_CHUNK])
    groups_loaded = len(groups)
    groups_next_offset = groups_loaded
    groups_has_more = groups_next_offset < groups_total

    perms_qs = _permissions_queryset(perm_q)
    perm_total = perms_qs.count()
    permissions = list(perms_qs[:ACCESS_LIST_CHUNK])
    perm_loaded = len(permissions)
    perm_next_offset = perm_loaded
    perm_has_more = perm_next_offset < perm_total

    return {
        "group_q": group_q,
        "perm_q": perm_q,
        "groups": groups,
        "groups_total": groups_total,
        "groups_next_offset": groups_next_offset,
        "groups_has_more": groups_has_more,
        "access_list_chunk": ACCESS_LIST_CHUNK,
        "permissions": permissions,
        "perm_total": perm_total,
        "perm_next_offset": perm_next_offset,
        "perm_has_more": perm_has_more,
        "django_groups_ui_name": DJANGO_GROUPS_UI_NAME,
    }


@require_http_methods(["GET"])
def access_management_index(request: HttpRequest) -> HttpResponse:
    fmt = request.GET.get("format", "").strip()
    group_q = request.GET.get("group_q", "").strip()
    perm_q = request.GET.get("perm_q", "").strip()

    if fmt == "htmx-access-groups-panel":
        groups_qs = _groups_queryset(group_q)
        groups_total = groups_qs.count()
        groups = list(groups_qs[:ACCESS_LIST_CHUNK])
        groups_next_offset = len(groups)
        return render(
            request,
            "access_management/_access_groups_panel.html",
            {
                "group_q": group_q,
                "groups": groups,
                "groups_total": groups_total,
                "groups_next_offset": groups_next_offset,
                "groups_has_more": groups_next_offset < groups_total,
                "access_list_chunk": ACCESS_LIST_CHUNK,
                "django_groups_ui_name": DJANGO_GROUPS_UI_NAME,
            },
        )

    if fmt == "htmx-access-groups-append":
        offset = _non_negative_offset(request)
        groups_qs = _groups_queryset(group_q)
        groups_total = groups_qs.count()
        groups = list(groups_qs[offset : offset + ACCESS_LIST_CHUNK])
        next_offset = offset + len(groups)
        return render(
            request,
            "access_management/_access_groups_append.html",
            {
                "group_q": group_q,
                "groups": groups,
                "groups_total": groups_total,
                "groups_next_offset": next_offset,
                "groups_has_more": next_offset < groups_total,
                "access_list_chunk": ACCESS_LIST_CHUNK,
                "django_groups_ui_name": DJANGO_GROUPS_UI_NAME,
            },
        )

    if fmt == "htmx-access-permissions-panel":
        perms_qs = _permissions_queryset(perm_q)
        perm_total = perms_qs.count()
        permissions = list(perms_qs[:ACCESS_LIST_CHUNK])
        perm_next_offset = len(permissions)
        return render(
            request,
            "access_management/_access_permissions_panel.html",
            {
                "perm_q": perm_q,
                "permissions": permissions,
                "perm_total": perm_total,
                "perm_next_offset": perm_next_offset,
                "perm_has_more": perm_next_offset < perm_total,
                "access_list_chunk": ACCESS_LIST_CHUNK,
                "django_groups_ui_name": DJANGO_GROUPS_UI_NAME,
            },
        )

    if fmt == "htmx-access-permissions-append":
        offset = _non_negative_offset(request)
        perms_qs = _permissions_queryset(perm_q)
        perm_total = perms_qs.count()
        permissions = list(perms_qs[offset : offset + ACCESS_LIST_CHUNK])
        next_offset = offset + len(permissions)
        return render(
            request,
            "access_management/_access_permissions_append.html",
            {
                "perm_q": perm_q,
                "permissions": permissions,
                "perm_total": perm_total,
                "perm_next_offset": next_offset,
                "perm_has_more": next_offset < perm_total,
                "access_list_chunk": ACCESS_LIST_CHUNK,
                "django_groups_ui_name": DJANGO_GROUPS_UI_NAME,
            },
        )

    ctx = _access_management_index_context(request)
    return render(request, "access_management/index.html", ctx)


@require_http_methods(["GET"])
def administration_permissions(request: HttpRequest) -> HttpResponse:
    """Canonical permissions collection URL with format=htmx-search-results dropdown."""
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
    groups = Group.objects.filter(permissions=permission).order_by("name").distinct()
    return render(
        request,
        "access_management/permission_detail.html",
        {
            "permission": permission,
            "groups": groups,
            "django_groups_ui_name": DJANGO_GROUPS_UI_NAME,
        },
    )
