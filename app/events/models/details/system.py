from django.db import models

from app.events.models.event import Event, EventType


class SystemDetail(Event):
    """
    Detail table for event_type='system'.

    Covers system-level events: outages, deployments, configuration changes, etc.
    """

    affected_component = models.CharField(max_length=255, blank=True)
    severity = models.CharField(
        max_length=20,
        choices=[
            ("info", "Info"),
            ("warning", "Warning"),
            ("error", "Error"),
            ("critical", "Critical"),
        ],
        blank=True,
    )

    class Meta:
        db_table = "event_detail_system"

    def save(self, *args, **kwargs) -> None:
        self.event_type = EventType.SYSTEM
        super().save(*args, **kwargs)
