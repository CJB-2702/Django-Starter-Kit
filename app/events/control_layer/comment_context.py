"""CommentContext — stateful control object for a single comment."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import transaction

from app.events.control_layer.domain_structs.comment_struct import CommentStruct

if TYPE_CHECKING:
    from app.events.models import CommentAttachment, Event, EventComment


class CommentContext:
    """
    Owns the delete cascade for a comment: soft-deletes the comment,
    its active attachment rows, and any files that become orphaned.

    No create() method — adding a comment is handled by CommentHandler.
    """

    def __init__(self, comment_id: int, actor) -> None:
        self.struct = CommentStruct(comment_id)
        self.actor = actor
        self._event = None
        self._domain = None

    @classmethod
    def create_from_struct(cls, comment_struct: CommentStruct, actor) -> "CommentContext":
        """Build from a pre-loaded struct. Issues no DB queries."""
        instance = cls.__new__(cls)
        instance.struct = comment_struct
        instance.actor = actor
        instance._event = None
        instance._domain = None
        return instance

    @property
    def event(self):
        if self._event is None:
            from app.events.models import Event
            self._event = Event.objects.select_related("domain").get(
                pk=self.struct.comment.event_id
            )
        return self._event

    @property
    def domain(self):
        if self._domain is None:
            self._domain = self.event.domain
        return self._domain

    def edit(self, post_data) -> object:
        from app.events.control_layer.handlers.comment_handler import CommentHandler
        return CommentHandler(self.actor).edit(self.struct.comment, post_data)

    def delete(self) -> None:
        from app.events.control_layer.handlers.file_handler import FileHandler
        from app.events.models import CommentAttachment

        with transaction.atomic():
            self.struct.comment._soft_delete(self.actor)

            for attachment in self.struct.attachments:
                attachment._soft_delete(self.actor)

                still_referenced = CommentAttachment.objects.filter(
                    file_id=attachment.file_id,
                    deleted_at__isnull=True,
                ).exists()

                if not still_referenced:
                    FileHandler(self.actor).soft_delete(attachment.file)
