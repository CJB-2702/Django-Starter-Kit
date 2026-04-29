from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.models import Group
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.text import slugify
from django.views.decorators.http import require_http_methods

from app.administration.control_layer.permissions.permission_grant_guard import (
    GrantPermissionDenied,
    is_admin_actor,
)
from app.administration.control_layer.permissions.permission_group_template_context import (
    PermissionGroupTemplateContext,
)
from app.administration.control_layer.permissions.template_assignment_guard import (
    assert_actor_may_edit_templates,
)
from app.administration.models import (
    PermissionGroupTemplate,
    PermissionGroupTemplateItem,
    UserPermissionGroupTemplate,
)


def _require_admin(request: HttpRequest) -> HttpResponse | None:
    if not is_admin_actor(request.user):
        return HttpResponseForbidden(
            "Only generic_admin or Django superusers may manage permission group templates.",
        )
    return None


def _parse_id_list(post, key: str) -> list[int]:
    out: list[int] = []
    for raw in post.getlist(key):
        try:
            out.append(int(raw))
        except ValueError:
            continue
    return out


@require_http_methods(["GET", "POST"])
def permission_group_template_index(request: HttpRequest) -> HttpResponse:
    """List templates with item and assignee counts; admin-only create form."""
    if request.method == "POST":
        denied = _require_admin(request)
        if denied is not None:
            return denied
        actor = request.user
        action = request.POST.get("action", "")
        try:
            if action == "create_template":
                assert_actor_may_edit_templates(actor)
                name = request.POST.get("name", "").strip()
                description = request.POST.get("description", "").strip()
                if not name:
                    messages.error(request, "Template name is required.")
                else:
                    slug_base = slugify(name) or "template"
                    slug = slug_base
                    suffix = 2
                    while PermissionGroupTemplate.objects.filter(slug=slug).exists():
                        slug = f"{slug_base}-{suffix}"
                        suffix += 1
                    PermissionGroupTemplate.objects.create(
                        name=name,
                        slug=slug,
                        description=description,
                        is_active=True,
                        created_by=actor,
                        updated_by=actor,
                    )
                    messages.success(request, f"Created template '{name}'.")
            else:
                messages.error(request, "Unknown action.")
        except GrantPermissionDenied as exc:
            messages.error(request, str(exc))
        return redirect(reverse("permission_group_template_index"))

    templates = list(
        PermissionGroupTemplate.objects.order_by("name").prefetch_related("items"),
    )
    template_rows = []
    for tpl in templates:
        item_count = tpl.items.count()
        assignee_count = UserPermissionGroupTemplate.objects.filter(template=tpl).count()
        template_rows.append(
            {
                "template": tpl,
                "item_count": item_count,
                "assignee_count": assignee_count,
            },
        )

    return render(
        request,
        "permissions_portal/template_index.html",
        {
            "template_rows": template_rows,
            "can_edit": is_admin_actor(request.user),
        },
    )


@require_http_methods(["GET", "POST"])
def permission_group_template_detail(
    request: HttpRequest,
    template_slug: str,
) -> HttpResponse:
    """Edit a single template: items, name/description, active flag."""
    template = get_object_or_404(PermissionGroupTemplate, slug=template_slug)

    if request.method == "POST":
        denied = _require_admin(request)
        if denied is not None:
            return denied
        actor = request.user
        action = request.POST.get("action", "")
        ctx = PermissionGroupTemplateContext(template.pk)
        try:
            if action == "add_permission_groups":
                ids = _parse_id_list(request.POST, "permission_group_ids")
                if not ids:
                    messages.error(request, "Select at least one permission group to add.")
                else:
                    with transaction.atomic():
                        for gid in ids:
                            ctx.add_permission_group(actor=actor, group_id=gid)
                    messages.success(request, "Permission groups added to template.")
            elif action == "remove_permission_groups":
                ids = _parse_id_list(request.POST, "permission_group_ids")
                if not ids:
                    messages.error(request, "Select at least one permission group to remove.")
                else:
                    with transaction.atomic():
                        for gid in ids:
                            ctx.remove_permission_group(actor=actor, group_id=gid)
                    messages.success(request, "Permission groups removed from template.")
            elif action == "update_metadata":
                name = request.POST.get("name", "").strip() or None
                description = request.POST.get("description", "")
                ctx.update_metadata(actor=actor, name=name, description=description)
                messages.success(request, "Template details updated.")
            elif action == "set_active":
                is_active = request.POST.get("is_active") == "1"
                ctx.set_active(actor=actor, is_active=is_active)
                messages.success(
                    request,
                    "Template activated." if is_active else "Template deactivated.",
                )
            else:
                messages.error(request, "Unknown action.")
        except GrantPermissionDenied as exc:
            messages.error(request, str(exc))
        except (ObjectDoesNotExist, ValueError) as exc:
            messages.error(request, str(exc))
        return redirect(
            reverse(
                "permission_group_template_detail",
                kwargs={"template_slug": template.slug},
            ),
        )

    assigned_group_ids = list(
        PermissionGroupTemplateItem.objects.filter(template=template).values_list(
            "permission_group_id",
            flat=True,
        ),
    )
    permission_groups_assigned = list(
        Group.objects.filter(pk__in=assigned_group_ids).order_by("name"),
    )
    permission_groups_available = list(
        Group.objects.exclude(pk__in=assigned_group_ids).order_by("name"),
    )
    assignees = list(
        UserPermissionGroupTemplate.objects.filter(template=template)
        .select_related("user")
        .order_by("user__username"),
    )

    return render(
        request,
        "permissions_portal/template_detail.html",
        {
            "template": template,
            "permission_groups_available": permission_groups_available,
            "permission_groups_assigned": permission_groups_assigned,
            "assignees": assignees,
            "can_edit": is_admin_actor(request.user),
        },
    )
