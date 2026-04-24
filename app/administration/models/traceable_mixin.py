from app.administration.models.auditable_mixin import AuditFieldsMixin
from django.db import models


class TraceableHistoryMixin(AuditFieldsMixin):
    """Extends AuditFieldsMixin with history tracking, soft deletes, and revision control."""

    origin_id = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        related_name="+",
        null=True,
        blank=True,
    )
    deleted_at = models.DateTimeField(null=True, blank=True)
    revision = models.IntegerField(default=1)

    class Meta:
        abstract = True
