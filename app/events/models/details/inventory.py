from django.db import models

from app.events.models.event import Event, EventType


class InventoryDetail(Event):
    """
    Detail table for event_type='inventory'.

    Covers stock takes, discrepancies, receiving events, etc.
    """

    item_category = models.CharField(max_length=255, blank=True)
    location_reference = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "event_detail_inventory"

    def save(self, *args, **kwargs) -> None:
        self.event_type = EventType.INVENTORY
        super().save(*args, **kwargs)
