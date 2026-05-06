from django.contrib.auth.decorators import login_not_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods


@login_not_required
@require_http_methods(["GET"])
def docs_administration_overview(request: HttpRequest) -> HttpResponse:
    return render(request, "docs/adm_overview.html", {})


@login_not_required
@require_http_methods(["GET"])
def docs_administration_roles(request: HttpRequest) -> HttpResponse:
    return render(request, "docs/adm_roles.html", {})


@login_not_required
@require_http_methods(["GET"])
def docs_administration_data_domains(request: HttpRequest) -> HttpResponse:
    return render(request, "docs/adm_data_domains.html", {})


@login_not_required
@require_http_methods(["GET"])
def docs_administration_domain_templates(request: HttpRequest) -> HttpResponse:
    return render(request, "docs/adm_domain_templates.html", {})
