from django.apps import AppConfig

EVENT_PERMISSION_GROUPS = [
    "default_event_permissions",
    "can_edit_others_events",
    "can_delete_any_event",
    "can_edit_others_comments",
    "can_view_deleted_comments_events_attachments",
]


class EventsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "app.events"
    label = "events"
    verbose_name = "Events"

    def ready(self) -> None:
        from django.db.models.signals import post_migrate

        post_migrate.connect(_ensure_permission_groups, sender=self)


def _ensure_permission_groups(sender, **kwargs) -> None:
    """Create the event permission groups if they don't exist."""
    from django.contrib.auth.models import Group

    for name in EVENT_PERMISSION_GROUPS:
        Group.objects.get_or_create(name=name)
