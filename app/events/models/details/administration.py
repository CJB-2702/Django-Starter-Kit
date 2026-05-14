from django.db import models

from app.events.models.event import Event, EventType


class AdministrationDetail(Event):
    """
    Detail table for event_type='administration'.

    Covers administrative events: audits, policy changes, staff actions, etc.
    """

    department = models.CharField(max_length=255, blank=True)
    reference_number = models.CharField(max_length=100, blank=True)

    class Meta:
        db_table = "event_detail_administration"

    def save(self, *args, **kwargs) -> None:
        self.event_type = EventType.ADMINISTRATION
        super().save(*args, **kwargs)
