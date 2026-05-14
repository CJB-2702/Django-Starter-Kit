

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from django.db.models import Prefetch

from app.events.control_layer.domain_structs.comment_struct import CommentStruct

if TYPE_CHECKING:
    from app.events.models import CommentAttachment, Event, EventComment, EventFile


class BaseEventStruct:
    """
    BaseEventStruct — data container for a single Event and its entire child graph.

    Loads the event, all of its comments, all comment attachments, and all
    referenced files in exactly 3 SQL queries regardless of tree depth:
    1. Event row (+ domain, created_by via JOIN)
    2. All comments for that event (+ created_by via JOIN)
    3. All attachments across those comments (+ file via JOIN)

    3 queries is the irreducible minimum for this 3-level tree with the Django ORM;
    going below that requires a denormalising JOIN which produces O(comments×attachments)
    rows and is slower in practice.

    Relationships:
    Event (1)
        └── EventComment (0..N)   related_name="comments"
            └── CommentAttachment (0..N)   related_name="attachments"
                    └── EventFile (1 per attachment)
    """
    def __init__(self, event_id: int, include_shadow_comments: bool = False) -> None:
        from app.events.models import CommentAttachment, Event, EventComment

        attachment_prefetch = Prefetch(
            "attachments",
            queryset=CommentAttachment.objects.filter(
                deleted_at__isnull=True
            ).select_related("file"),
            to_attr="loaded_attachments",
        )

        comment_qs = (
            EventComment.objects.filter(deleted_at__isnull=True)
            .select_related("created_by")
            .prefetch_related(attachment_prefetch)
        )
        if not include_shadow_comments:
            comment_qs = comment_qs.filter(is_human_made=True)

        # 3 queries total: event + comments prefetch + attachments prefetch
        event = (
            Event.objects.select_related("domain", "created_by")
            .prefetch_related(Prefetch("comments", queryset=comment_qs, to_attr="loaded_comments"))
            .get(pk=event_id)
        )

        self.event: Event = event
        self.comments: list[CommentStruct] = [
            CommentStruct.from_components(
                c, c.loaded_attachments, [a.file for a in c.loaded_attachments]
            )
            for c in event.loaded_comments
        ]

    @classmethod
    def from_components(
        cls,
        event_row: "Event",
        comment_rows: "list[EventComment]",
        attachment_rows: "list[CommentAttachment]",
        file_rows: "list[EventFile]",
    ) -> "BaseEventStruct":
        """Build from pre-fetched rows. Issues no DB queries."""
        instance = cls.__new__(cls)
        instance.event = event_row
        instance.comments = cls._build_comment_structs(comment_rows, attachment_rows, file_rows)
        return instance

    @staticmethod
    def _build_comment_structs(
        comment_rows: "list[EventComment]",
        attachment_rows: "list[CommentAttachment]",
        file_rows: "list[EventFile]",
    ) -> "list[CommentStruct]":
        attachments_by_comment: dict[int, list] = defaultdict(list)
        for att in attachment_rows:
            attachments_by_comment[att.comment_id].append(att)

        comment_structs = []
        for comment in comment_rows:
            atts = attachments_by_comment.get(comment.pk, [])
            files = [a.file for a in atts]
            comment_structs.append(CommentStruct.from_components(comment, atts, files))
        return comment_structs

    def to_dict(self) -> dict:
        from app.utils.hashids import encode_id

        return {
            "event_id": self.event.pk,
            "event_hash": encode_id(self.event.pk),
            "title": self.event.title,
            "description": self.event.description,
            "event_type": self.event.event_type,
            "status": self.event.status,
            "priority": self.event.priority,
            "event_start": self.event.event_start.isoformat() if self.event.event_start else None,
            "event_end": self.event.event_end.isoformat() if self.event.event_end else None,
            "domain": self.event.domain.name if self.event.domain else None,
            "created_by": str(self.event.created_by) if self.event.created_by else None,
            "created_at": self.event.created_at.isoformat() if self.event.created_at else None,
            "comments": [c.to_dict() for c in self.comments],
        }
