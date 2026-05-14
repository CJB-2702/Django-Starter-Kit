"""Event base model — all common fields live here."""

from __future__ import annotations

from django.db import models
from django.utils import timezone

from app.administration.models.auditable_mixin import AuditFieldsMixin
from app.administration.models.soft_delete_mixin import SoftDeleteMixin


class EventType(models.TextChoices):
    GENERIC = "generic", "Generic"
    SYSTEM = "system", "System"
    ADMINISTRATION = "administration", "Administration"
    ASSET_MANAGEMENT = "asset_management", "Asset Management"
    INVENTORY = "inventory", "Inventory"
    DISPATCHING = "dispatching", "Dispatching"
    MAINTENANCE = "maintenance", "Maintenance"


class EventStatus(models.TextChoices):
    PLANNED = "planned", "Planned"
    IN_PROGRESS = "in_progress", "In Progress"
    COMPLETE = "complete", "Complete"
    CANCELLED = "cancelled", "Cancelled"
    FAILED = "failed", "Failed"
    SKIPPED = "skipped", "Skipped"
    BLOCKED = "blocked", "Blocked"


# Statuses that clear priority on transition.
PRIORITY_CLEARING_STATUSES = {
    EventStatus.COMPLETE,
    EventStatus.CANCELLED,
    EventStatus.FAILED,
    EventStatus.SKIPPED,
}


class EventPriority(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"
    CRITICAL = "critical", "Critical"


class EventQuerySet(models.QuerySet):
    def active(self) -> EventQuerySet:
        return self.filter(deleted_at__isnull=True)

    def deleted(self) -> EventQuerySet:
        return self.filter(deleted_at__isnull=False)

    def visible_to(self, user) -> EventQuerySet:
        """Return events the user may see: in their domains OR created by them."""
        from app.administration.models.data_ownership.user_assignments.user_domains import (
            UserDomain,
        )

        user_domain_ids = UserDomain.objects.filter(
            user=user, is_active=True
        ).values_list("domain_id", flat=True)

        return self.active().filter(
            models.Q(domain_id__in=user_domain_ids) | models.Q(created_by=user)
        )


class EventManager(models.Manager):
    def get_queryset(self) -> EventQuerySet:
        return EventQuerySet(self.model, using=self._db)

    def active(self) -> EventQuerySet:
        return self.get_queryset().active()

    def visible_to(self, user) -> EventQuerySet:
        return self.get_queryset().visible_to(user)


class Event(AuditFieldsMixin, SoftDeleteMixin):
    """
    Base event record. All event types share these columns.
    Integer PK is never exposed in URLs — hashid-encoded at the URL boundary.
    has comments, comment attachments, and comment files.
    """

    domain = models.ForeignKey(
        "administration.Domain",
        on_delete=models.PROTECT,
        related_name="events",
    )

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    event_type = models.CharField(
        max_length=50,
        choices=EventType.choices,
        default=EventType.GENERIC,
    )

    status = models.CharField(
        max_length=20,
        choices=EventStatus.choices,
        default=EventStatus.PLANNED,
    )

    priority = models.CharField(
        max_length=20,
        choices=EventPriority.choices,
        null=True,
        blank=True,
        default=None,
    )

    event_start = models.DateTimeField(null=True, blank=True)
    event_end = models.DateTimeField(null=True, blank=True)

    objects = EventManager()

    class Meta:
        db_table = "event"
        ordering = ["-created_at"]

    def _soft_delete(self, actor=None) -> None:
        self.deleted_at = timezone.now()
        update_fields = ["deleted_at"]
        if actor is not None:
            self.updated_by = actor
            update_fields.append("updated_by")
        self.save(update_fields=update_fields)

    def __str__(self) -> str:
        return f"[{self.get_event_type_display()}] {self.title}"
