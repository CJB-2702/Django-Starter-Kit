"""Permissions: read-only list and detail (Django auth.Permission is not editable)."""

from __future__ import annotations

from django.contrib.auth.models import Group, Permission
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods


@require_http_methods(["GET"])
def permission_index(request: HttpRequest) -> HttpResponse:
    q = request.GET.get("q", "").strip()
    qs = Permission.objects.select_related("content_type").order_by(
        "content_type__app_label",
        "content_type__model",
        "codename",
    )
    if q:
        qs = qs.filter(
            Q(codename__icontains=q)
            | Q(name__icontains=q)
            | Q(content_type__app_label__icontains=q)
            | Q(content_type__model__icontains=q),
        )
    page_size = 50
    paginator = Paginator(qs, page_size)
    page = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "permissions/permissions/index.html",
        {
            "page": page,
            "q": q,
        },
    )


@require_http_methods(["GET"])
def permission_detail(request: HttpRequest, permission_id: int) -> HttpResponse:
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
        "permissions/permissions/detail.html",
        {
            "permission": permission,
            "groups": groups,
        },
    )
