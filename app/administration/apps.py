from django.apps import AppConfig


class AdministrationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "app.administration"
    label = "administration"
    verbose_name = "Administration"

    def ready(self) -> None:
        from django.contrib.auth.signals import user_logged_in

        from app.administration.auth_session import refresh_auth_in_session

        def on_user_logged_in(sender, request, user, **kwargs):
            refresh_auth_in_session(request, user)

        user_logged_in.connect(
            on_user_logged_in,
            dispatch_uid="administration.refresh_auth_in_session",
        )
