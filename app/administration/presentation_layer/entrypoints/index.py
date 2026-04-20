from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def administration_index(request: HttpRequest) -> HttpResponse:
    return render(request, "adm_index.html", {})
