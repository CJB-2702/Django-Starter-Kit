from django.urls import path

from app.public_app.presentation_layer.entrypoints.about import public_about
from app.public_app.presentation_layer.entrypoints.docs.administration import (
    docs_administration_data_domains,
    docs_administration_domain_templates,
    docs_administration_overview,
    docs_administration_roles,
)
from app.public_app.presentation_layer.entrypoints.home import public_home
from app.public_app.presentation_layer.entrypoints.logout import PublicLogoutView

urlpatterns = [
    path("", public_home, name="public_home"),
    path("about/", public_about, name="public_about"),
    path("site/about/", public_about, name="public_about_site_path"),
    path(
        "logout/",
        PublicLogoutView.as_view(),
        name="public_logout",
    ),
    path("docs/administration/", docs_administration_overview, name="docs_administration_overview"),
    path("docs/administration/roles/", docs_administration_roles, name="docs_administration_roles"),
    path("docs/administration/data-domains/", docs_administration_data_domains, name="docs_administration_data_domains"),
    path("docs/administration/domain-templates/", docs_administration_domain_templates, name="docs_administration_domain_templates"),
]
