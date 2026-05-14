from django.db import models

from app.events.models.event import Event, EventType


class DispatchingDetail(Event):
    """
    Detail table for event_type='dispatching'.

    Covers dispatch orders, route assignments, resource allocations, etc.
    """

    destination = models.CharField(max_length=255, blank=True)
    resource_reference = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "event_detail_dispatching"

    def save(self, *args, **kwargs) -> None:
        self.event_type = EventType.DISPATCHING
        super().save(*args, **kwargs)
