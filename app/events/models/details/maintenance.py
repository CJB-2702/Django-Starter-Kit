from django.db import models

from app.events.models.event import Event, EventType


class MaintenanceDetail(Event):
    """
    Detail table for event_type='maintenance'.

    Covers scheduled maintenance, reactive repairs, inspections, etc.
    """

    maintenance_type = models.CharField(
        max_length=50,
        choices=[
            ("scheduled", "Scheduled"),
            ("reactive", "Reactive"),
            ("inspection", "Inspection"),
            ("preventive", "Preventive"),
        ],
        blank=True,
    )
    work_order_reference = models.CharField(max_length=100, blank=True)
    maintenance_schedule = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "event_detail_maintenance"

    def save(self, *args, **kwargs) -> None:
        self.event_type = EventType.MAINTENANCE
        super().save(*args, **kwargs)
