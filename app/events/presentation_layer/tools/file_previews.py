"""File preview utilities — read-only, presentation layer only."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.events.control_layer.domain_structs.base_event_struct import BaseEventStruct
    from app.events.models import EventFile


def get_text_snippet(event_file: "EventFile", max_chars: int = 50) -> str:
    try:
        with event_file.file.open("r") as fh:
            return fh.read(max_chars)
    except Exception:
        return ""


def build_comments_context(struct: "BaseEventStruct") -> list[dict]:
    """
    Process a BaseEventStruct into a flat list for template rendering.
    Each entry: {comment, comment_hash, attachments: [{attachment, snippet}]}
    """
    from app.utils.hashids import encode_id

    result = []
    for comment_struct in struct.comments:
        att_data = []
        for att in comment_struct.attachments:
            if att.file.deleted_at is not None:
                continue
            snippet = get_text_snippet(att.file) if att.file.is_text_preview() else None
            att_data.append({"attachment": att, "snippet": snippet})
        result.append({
            "comment": comment_struct.comment,
            "comment_hash": encode_id(comment_struct.comment.pk),
            "attachments": att_data,
        })
    return result
