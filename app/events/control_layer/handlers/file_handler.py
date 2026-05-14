"""FileHandler — upload, attach, and soft-delete EventFile rows."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from django.db import transaction
from django.utils import timezone

from app.events.models import CommentAttachment, AttachmentType, EventComment, EventFile
from app.events.models.file import ALLOWED_EXTENSIONS, MAX_FILE_SIZE_BYTES

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser
    from django.core.files.uploadedfile import UploadedFile


@dataclass
class FileResult:
    ok: bool
    file: EventFile | None = None
    errors: list[str] = field(default_factory=list)


class FileHandler:
    """Handles file upload, attachment linking, and soft-delete."""

    def __init__(self, actor: "AbstractUser") -> None:
        self.actor = actor

    def upload(self, comment: EventComment, uploaded_file: "UploadedFile | None") -> FileResult:
        if not uploaded_file or not getattr(uploaded_file, "name", None):
            return FileResult(ok=False, errors=["No file provided."])

        errors = self._validate(uploaded_file)
        if errors:
            return FileResult(ok=False, errors=errors)

        with transaction.atomic():
            event_file = EventFile.objects.create(
                file=uploaded_file,
                original_filename=uploaded_file.name,
                file_size=uploaded_file.size,
                mime_type=uploaded_file.content_type or "",
                created_by=self.actor,
                updated_by=self.actor,
            )
            attachment_type = self._infer_attachment_type(uploaded_file.name)
            existing_count = CommentAttachment.objects.filter(
                comment=comment, deleted_at__isnull=True
            ).count()
            CommentAttachment.objects.create(
                comment=comment,
                file=event_file,
                attachment_type=attachment_type,
                display_order=existing_count,
                created_by=self.actor,
                updated_by=self.actor,
            )

        return FileResult(ok=True, file=event_file)

    def soft_delete(self, event_file: EventFile) -> FileResult:
        """
        Soft-delete a file and bulk soft-delete all its attachment rows.
        Unconditional — the caller has already established intent.
        """
        with transaction.atomic():
            now = timezone.now()
            CommentAttachment.objects.filter(file=event_file).update(
                deleted_at=now,
                updated_by=self.actor,
                updated_at=now,
            )
            event_file._soft_delete(actor=self.actor)

        return FileResult(ok=True, file=event_file)

    # ------------------------------------------------------------------ #
    # Private helpers
    # ------------------------------------------------------------------ #

    def _validate(self, uploaded_file: "UploadedFile") -> list[str]:
        errors: list[str] = []
        name = getattr(uploaded_file, "name", None) or ""
        if not name:
            return ["File has no name."]
        if uploaded_file.size > MAX_FILE_SIZE_BYTES:
            errors.append("File exceeds maximum size of 100 MB.")
        if not EventFile.is_allowed_extension(name):
            ext = Path(name).suffix.lower()
            errors.append(f"File type '{ext}' is not allowed.")
        return errors

    def _infer_attachment_type(self, filename: str) -> str:
        ext = Path(filename).suffix.lower()
        if ext in ALLOWED_EXTENSIONS.get("images", set()):
            return AttachmentType.IMAGE
        return AttachmentType.DOCUMENT
