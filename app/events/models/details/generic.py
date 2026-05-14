from django.db import models

from app.events.models.event import Event, EventType


class GenericDetail(Event):
    """
    Detail table for event_type='generic'.

    No type-specific fields yet. Extend here as requirements emerge.
    """

    class Meta:
        db_table = "event_detail_generic"

    def save(self, *args, **kwargs) -> None:
        self.event_type = EventType.GENERIC
        super().save(*args, **kwargs)
