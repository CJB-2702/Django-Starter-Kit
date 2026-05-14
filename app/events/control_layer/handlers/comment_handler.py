"""CommentHandler — add and edit comments, with attachment carry-forward on edit."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from django.db import transaction
from django.utils import timezone

from app.events.models import CommentAttachment, Event, EventComment

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser


@dataclass
class CommentResult:
    ok: bool
    comment: EventComment | None = None
    errors: list[str] = field(default_factory=list)


class CommentHandler:
    """Handles create and edit operations on EventComment rows."""

    def __init__(self, actor: "AbstractUser") -> None:
        self.actor = actor

    def add(self, event: Event, post_data, files=None) -> CommentResult:
        content = post_data.get("content", "").strip()
        if not content:
            return CommentResult(ok=False, errors=["Comment content is required."])

        uploaded_file = files.get("file") if files else None
        if uploaded_file and not getattr(uploaded_file, "name", None):
            uploaded_file = None

        with transaction.atomic():
            comment = EventComment.objects.create(
                event=event,
                content=content,
                is_human_made=True,
                revision=1,
                created_by=self.actor,
                updated_by=self.actor,
            )

            if uploaded_file:
                from app.events.control_layer.handlers.file_handler import FileHandler
                result = FileHandler(self.actor).upload(comment, uploaded_file)
                if not result.ok:
                    transaction.set_rollback(True)
                    return CommentResult(ok=False, errors=result.errors)

        return CommentResult(ok=True, comment=comment)

    def edit(self, old_comment: EventComment, post_data, files=None) -> CommentResult:
        """
        Editing a comment:
          1. Soft-delete the old revision's active CommentAttachment rows.
          2. Soft-delete the old comment.
          3. Create a new comment (new revision) with new CommentAttachment rows
             pointing to the same EventFile rows.
        """
        content = post_data.get("content", "").strip()
        if not content:
            return CommentResult(ok=False, errors=["Comment content cannot be blank."])

        with transaction.atomic():
            now = timezone.now()

            # Soft-delete old revision's active attachment rows first.
            CommentAttachment.objects.filter(
                comment=old_comment, deleted_at__isnull=True
            ).update(deleted_at=now, updated_by=self.actor, updated_at=now)

            old_comment.deleted_at = now
            old_comment.updated_by = self.actor
            old_comment.save(update_fields=["deleted_at", "updated_by", "updated_at"])

            new_comment = EventComment.objects.create(
                event=old_comment.event,
                content=content,
                is_human_made=True,
                origin_id=old_comment,
                revision=old_comment.revision + 1,
                created_by=self.actor,
                updated_by=self.actor,
            )

            self._carry_forward_attachments(old_comment, new_comment)

            if files:
                uploaded_file = files.get("file")
                if uploaded_file and getattr(uploaded_file, "name", None):
                    from app.events.control_layer.handlers.file_handler import FileHandler
                    file_result = FileHandler(self.actor).upload(new_comment, uploaded_file)
                    if not file_result.ok:
                        transaction.set_rollback(True)
                        return CommentResult(ok=False, errors=file_result.errors)

        return CommentResult(ok=True, comment=new_comment)

    # ------------------------------------------------------------------ #
    # Private helpers
    # ------------------------------------------------------------------ #

    def _carry_forward_attachments(
        self, old_comment: EventComment, new_comment: EventComment
    ) -> None:
        """
        Duplicate attachment rows from old revision onto the new one.
        Queries all attachment rows for old_comment (including just-soft-deleted ones)
        so the same files appear on the new revision.
        """
        old_attachments = CommentAttachment.objects.filter(comment=old_comment)
        for att in old_attachments:
            CommentAttachment.objects.create(
                comment=new_comment,
                file=att.file,
                attachment_type=att.attachment_type,
                caption=att.caption,
                display_order=att.display_order,
                created_by=self.actor,
                updated_by=self.actor,
            )
