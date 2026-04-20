from django.urls import path

from app.public_app.presentation_layer.entrypoints.about import public_about
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
]
