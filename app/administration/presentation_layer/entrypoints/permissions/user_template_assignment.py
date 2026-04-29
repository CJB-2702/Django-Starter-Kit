from __future__ import annotations

from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from app.administration.control_layer.permissions.permission_grant_guard import (
    GrantPermissionDenied,
    is_admin_actor,
)
from app.administration.control_layer.permissions.user_template_assignment_context import (
    UserTemplateAssignmentContext,
)


def _redirect_back(user_id: int) -> HttpResponse:
    return redirect(reverse("user_portal_edit", kwargs={"user_id": user_id}))


@require_http_methods(["POST"])
def user_template_assignment(request: HttpRequest, user_id: int) -> HttpResponse:
    """POST endpoint from the user portal: assign / re-rebase / disable / update notes."""
    if not is_admin_actor(request.user):
        return HttpResponseForbidden(
            "Only generic_admin or Django superusers may change template assignments.",
        )

    actor = request.user
    action = request.POST.get("action", "")
    ctx = UserTemplateAssignmentContext(user_id)

    try:
        if action == "assign_template":
            template_id_raw = request.POST.get("template_id", "").strip()
            if not template_id_raw.isdigit():
                messages.error(request, "Select a template to assign.")
                return _redirect_back(user_id)
            template_id = int(template_id_raw)
            notes = request.POST.get("notes", "").strip()
            additive = request.POST.get("additive") == "1"
            ctx.assign_template(
                actor=actor,
                template_id=template_id,
                notes=notes,
                additive=additive,
            )
            mode = "additive" if additive else "rebase"
            messages.success(request, f"Template assigned ({mode}).")
        elif action == "re_rebase":
            row = ctx.re_rebase_current(actor=actor)
            if row is None:
                messages.error(request, "User has no active template to re-rebase.")
            else:
                messages.success(request, "User permission groups re-synced to template.")
        elif action == "update_notes":
            notes = request.POST.get("notes", "")
            row = ctx.update_notes(actor=actor, notes=notes)
            if row is None:
                messages.error(request, "User has no active template assignment.")
            else:
                messages.success(request, "Template assignment notes updated.")
        elif action == "disable_template":
            row = ctx.disable_current(actor=actor)
            if row is None:
                messages.error(request, "User has no active template to disable.")
            else:
                messages.success(
                    request,
                    "Template assignment disabled and template-derived groups removed.",
                )
        else:
            messages.error(request, "Unknown action.")
    except GrantPermissionDenied as exc:
        messages.error(request, str(exc))
    except (ObjectDoesNotExist, ValueError) as exc:
        messages.error(request, str(exc))

    return _redirect_back(user_id)
