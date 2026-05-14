"""CommentAttachment — links an EventComment to an EventFile."""

from __future__ import annotations

from django.db import models
from django.utils import timezone

from app.administration.models.auditable_mixin import AuditFieldsMixin
from app.administration.models.soft_delete_mixin import SoftDeleteMixin
from app.events.utils import generate_uuid7


class AttachmentType(models.TextChoices):
    IMAGE = "image", "Image"
    DOCUMENT = "document", "Document"
    VIDEO = "video", "Video"


class CommentAttachmentQuerySet(models.QuerySet):
    def active(self) -> CommentAttachmentQuerySet:
        return self.filter(deleted_at__isnull=True)


class CommentAttachmentManager(models.Manager):
    def get_queryset(self) -> CommentAttachmentQuerySet:
        return CommentAttachmentQuerySet(self.model, using=self._db)

    def active(self) -> CommentAttachmentQuerySet:
        return self.get_queryset().active()


class CommentAttachment(AuditFieldsMixin, SoftDeleteMixin):
    """
    Join record linking a comment to a file. Part of the audit trail —
    old revision rows are soft-deleted rather than hard-deleted.

    FK constraints:
      comment → CASCADE  (hard-deletes if comment is hard-deleted; never fires in normal operation)
      file    → PROTECT  (preserves referential integrity in the historical record)
    """

    id = models.UUIDField(primary_key=True, default=generate_uuid7, editable=False)

    comment = models.ForeignKey(
        "events.EventComment",
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    file = models.ForeignKey(
        "events.EventFile",
        on_delete=models.PROTECT,
        related_name="attachment_links",
    )

    attachment_type = models.CharField(
        max_length=20,
        choices=AttachmentType.choices,
        default=AttachmentType.DOCUMENT,
    )
    caption = models.CharField(max_length=255, blank=True)
    display_order = models.PositiveIntegerField(default=0)

    objects = CommentAttachmentManager()

    class Meta:
        db_table = "event_comment_attachment"
        ordering = ["display_order", "created_at"]

    def _soft_delete(self, actor=None) -> None:
        self.deleted_at = timezone.now()
        update_fields = ["deleted_at"]
        if actor is not None:
            self.updated_by = actor
            update_fields.append("updated_by")
        self.save(update_fields=update_fields)

    def __str__(self) -> str:
        return f"Attachment {self.id} → Comment {self.comment_id}"
