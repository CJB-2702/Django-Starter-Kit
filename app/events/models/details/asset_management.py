from django.db import models

from app.events.models.event import Event, EventType


class AssetManagementDetail(Event):
    """
    Detail table for event_type='asset_management'.

    Asset-specific fields will be added here once the assets module is built.
    The asset <-> event M2M table lives in app/assets — not here.
    """

    class Meta:
        db_table = "event_detail_asset_management"

    def save(self, *args, **kwargs) -> None:
        self.event_type = EventType.ASSET_MANAGEMENT
        super().save(*args, **kwargs)
