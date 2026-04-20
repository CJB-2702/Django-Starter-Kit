from django.apps import AppConfig


class PublicAppConfig(AppConfig):
    """Public-facing site shell (homepage, about). Product folder name: public-app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "app.public_app"
    label = "public_app"
    verbose_name = "Public app"
