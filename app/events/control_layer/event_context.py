"""EventContext — stateful control object for a single event."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import transaction

from app.events.control_layer.domain_structs.base_event_struct import BaseEventStruct

if TYPE_CHECKING:
    from django.core.files.uploadedfile import UploadedFile


class EventContext:
    """
    Primary entry point for external callers working with an event.
    Owns cross-table write operations; delegates single-row writes to handlers.

    No create() method — event creation is handled by EventHandler.
    """

    def __init__(self, event_id: int, actor) -> None:
        self.struct = BaseEventStruct(event_id)
        self.actor = actor

    @classmethod
    def create_from_struct(cls, base_event_struct: BaseEventStruct, actor) -> "EventContext":
        """Build from a pre-loaded struct. Issues no DB queries."""
        instance = cls.__new__(cls)
        instance.struct = base_event_struct
        instance.actor = actor
        return instance

    def edit(self, post_data) -> object:
        from app.events.control_layer.handlers.event_handler import EventHandler
        return EventHandler(self.actor).edit(self.struct.event, post_data)

    def add_comment(self, post_data) -> object:
        from app.events.control_layer.handlers.comment_handler import CommentHandler
        return CommentHandler(self.actor).add(self.struct.event, post_data)

    def add_attachment(self, uploaded_file: "UploadedFile") -> object:
        """
        Attach a file directly to the event by creating a visible
        machine-generated comment as the carrier.
        """
        from app.events.control_layer.handlers.file_handler import FileHandler
        from app.events.models import EventComment

        with transaction.atomic():
            machine_comment = EventComment.objects.create(
                event=self.struct.event,
                content=f"File added: {uploaded_file.name}",
                is_human_made=False,
                deleted_at=None,
                revision=1,
                created_by=self.actor,
                updated_by=self.actor,
            )
            return FileHandler(self.actor).upload(machine_comment, uploaded_file)

    def delete(self) -> None:
        """
        Soft-delete the event, then cascade to all child comments.
        EventContext does not import CommentAttachment or EventFile directly —
        all child cleanup is delegated to CommentContext.
        """
        from app.events.control_layer.comment_context import CommentContext

        with transaction.atomic():
            self.struct.event._soft_delete(self.actor)

            for comment_struct in self.struct.comments:
                CommentContext.create_from_struct(comment_struct, self.actor).delete()
