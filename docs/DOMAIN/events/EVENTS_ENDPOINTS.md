# Events Endpoints — Handler vs Context Routing

**Status:** Draft v2 — design only, no code written.

This document covers every endpoint in the events app and answers one question for each: should the entrypoint call the handler directly, or route through a context class? For struct and context class descriptions see [EVENT_CONTEXT_DESIGN.md](EVENT_CONTEXT_DESIGN.md). For the slug-to-hashid migration see [PK_with_hashing_migration.md](PK_with_hashing_migration.md).

---

## General rule

**Go direct to the handler** when the operation affects only the object being acted on — no parent-child cleanup, no cross-table cascades.

**Use a context** when the operation has effects outside the object itself — particularly deletes where child rows and potentially orphaned files must also be cleaned up, or when the full event graph needs to be loaded in one pass.

Within this application, most write actions are simple CRUD on one row. The context is the exception, not the default.

---

## ID resolution pattern

All event and comment URLs expose a hashid-encoded integer PK. Slugs have been removed. The entrypoint is responsible for decoding the hashid to an integer PK and fetching the model instance before calling any handler or context.

```python
from app.utils.hashids import decode_hash

event_id = decode_hash(hash_str)        # returns int or None
event = get_object_or_404(Event.objects.active(), pk=event_id)
# Permission check uses fields on the resolved instance
# Handler or context is called after the permission check passes
```

The control layer (handlers, contexts, structs) works with integer PKs and model instances — never with hashids. Decoding is a presentation layer concern and stays in the entrypoint.

For file endpoints, the UUID7 is used directly in the URL — no hashid involved.

---

## Endpoints

### `GET /events/` — event list

**Routing:** Direct to search function (`list_events_for_user()`). No handler, no context.

**Rationale:** Read-only list. Does not load comment or attachment data — `BaseEventStruct` is not needed. The search function returns a queryset the template iterates.

---

### `GET /events/create/` — event create form

**Routing:** No handler call on GET. Renders the form.

---

### `POST /events/create/` — event create submit

**Routing:** Direct to `EventHandler.create()`.

**Rationale:** Creating an event has no children yet. Nothing to cascade to. `EventContext` has no `create()` method.

```
event_create() entrypoint
  └── EventHandler(actor).create(request.POST)
        └── EventResult(ok, event)
  → redirect to event_detail using encode_id(event.pk)
```

---

### `GET /events/<hash>/` — event detail

**Routing:** Build a `BaseEventStruct` (or `EventContext`) after resolving the hashid.

**Rationale:** The detail page needs the event row, all visible comments, and all attachments with their files. Without the struct this is N+1 queries (the current `build_attachment_context()` pattern).

```
event_detail() entrypoint
  ├── event_id = decode_hash(hash)
  ├── event = get_object_or_404(Event.objects.active(), pk=event_id)
  ├── permission check (domain membership, created_by)
  └── ctx = EventContext(event_id, actor)   ← 4 fixed queries
        → ctx.struct.event
        → ctx.struct.comments               ← list[CommentStruct], fully loaded
```

The permission check uses the already-fetched `event` instance. `EventContext` will re-fetch the event as part of `BaseEventStruct` — this is one extra query and is acceptable since the permission check requires the event fields before the context is built.

---

### `GET /events/<hash>/edit/` — event edit form

**Routing:** No handler call on GET. Decode hashid, fetch event, permission check, render form.

---

### `POST /events/<hash>/edit/` — event edit submit

**Routing:** Direct to `EventHandler.edit()`.

**Rationale:** Editing touches only the event row. The handler internally calls `_apply_shadow_comment()` and, when status or time fields change, `_apply_machine_comment()`. No cross-table effects that require a context.

```
event_edit() entrypoint
  ├── event_id = decode_hash(hash)
  ├── event = get_object_or_404(Event.objects.active(), pk=event_id)
  ├── permission check
  └── EventHandler(actor).edit(event, request.POST)
```

---

### `POST /events/<hash>/delete/` — event soft-delete

**Routing:** Through `EventContext.delete()`.

**Rationale:** This is the primary use case for a context within this application. Deleting an event must also soft-delete all child comments and soft-delete any files that become orphaned. The event model's `_soft_delete()` only marks the event row — the context owns the cascade.

```
event_soft_delete() entrypoint
  ├── event_id = decode_hash(hash)
  ├── event = get_object_or_404(Event.objects.active(), pk=event_id)
  ├── permission check (must happen before context — context is not a permission layer)
  └── ctx = EventContext(event_id, actor)
        └── ctx.delete()
              ├── event._soft_delete(actor)
              └── for each comment_struct in ctx.struct.comments:
                    CommentContext.create_from_struct(comment_struct, actor).delete()
                      ├── comment._soft_delete(actor)
                      └── orphaned files soft-deleted
```

---

### `GET /events/<hash>/comments/add/` — add comment form

**Routing:** No handler call on GET. Decode hashid, fetch event, render form.

---

### `POST /events/<hash>/comments/add/` — add comment submit

**Routing:** Direct to `CommentHandler.add()`.

**Rationale:** Adding a comment creates one row. No parent-child effects.

```
comment_add() entrypoint
  ├── event_id = decode_hash(event_hash)
  ├── event = get_object_or_404(Event.objects.active(), pk=event_id)
  └── CommentHandler(actor).add(event, request.POST)
```

---

### `GET /events/<hash>/comments/<hash>/edit/` — edit comment form

**Routing:** No handler call on GET. Decode both hashids, fetch event + comment, permission check, render form.

---

### `POST /events/<hash>/comments/<hash>/edit/` — edit comment submit

**Routing:** Direct to `CommentHandler.edit()`.

**Rationale:** Editing a comment creates a new revision, soft-deletes the old one, and carries forward attachment links. All of this is self-contained inside `CommentHandler.edit()` — no cross-table effects outside what the handler already manages.

```
comment_edit() entrypoint
  ├── event_id = decode_hash(event_hash)
  ├── comment_id = decode_hash(comment_hash)
  ├── event = get_object_or_404(Event.objects.active(), pk=event_id)
  ├── comment = get_object_or_404(EventComment.objects.active(), pk=comment_id, event=event)
  ├── permission check
  └── CommentHandler(actor).edit(comment, request.POST)
```

---

### `POST /events/<hash>/comments/<hash>/delete/` — comment soft-delete

**Routing:** Through `CommentContext.delete()`.

**Rationale:** Deleting a comment must check whether any files attached to that comment are now orphaned. `CommentContext.delete()` owns this check. The comment model's `_soft_delete()` only marks the comment row.

```
comment_soft_delete() entrypoint
  ├── event_id = decode_hash(event_hash)
  ├── comment_id = decode_hash(comment_hash)
  ├── event = get_object_or_404(Event.objects.active(), pk=event_id)
  ├── comment = get_object_or_404(EventComment.objects.active(), pk=comment_id, event=event)
  ├── permission check
  └── CommentContext(comment_id, actor).delete()
        ├── comment._soft_delete(actor)
        └── for each attachment:
              if no other CommentAttachment rows reference this file:
                FileHandler(actor).soft_delete(file)
```

---

### `POST /events/<hash>/files/upload/` — file upload

**Routing:** Direct to `FileHandler.upload()`.

**Rationale:** Uploading creates an `EventFile` row and one `CommentAttachment` link. Self-contained. The comment the file is attached to is identified by its hashid-decoded integer PK passed in POST data.

```
file_upload() entrypoint
  ├── event_id = decode_hash(event_hash)
  ├── event = get_object_or_404(Event.objects.active(), pk=event_id)
  ├── comment_id = decode_hash(request.POST.get("comment_id"))
  ├── comment = get_object_or_404(EventComment.objects.active(), pk=comment_id, event=event)
  ├── permission check
  └── FileHandler(actor).upload(comment, request.FILES.get("file"))
```

---

### `GET /events/files/<uuid>/download/` — file download

**Routing:** No handler. Resolve file by UUID7, serve directly.

**Rationale:** Read-only. Files and attachments keep UUID7 PKs — no hashid involved.

---

### `GET /events/files/<uuid>/inline/` — file inline

**Routing:** No handler. Resolve file by UUID7, serve directly.

**Rationale:** Read-only. No writes.

---

### `POST /events/files/<uuid>/delete/` — file soft-delete

**Routing:** Direct to `FileHandler.soft_delete()`.

**Rationale:** The user has explicitly chosen to delete this specific file, identified by its UUID7. `FileHandler.soft_delete()` handles the full cleanup: it hard-deletes all `CommentAttachment` rows referencing the file first, then soft-deletes the `EventFile` row. This is distinct from the orphan-check path inside `CommentContext.delete()` — that path only deletes a file when it determines the file has no remaining references. This path deletes unconditionally because the intent is explicit.

```
file_soft_delete() entrypoint
  ├── event_file = get_object_or_404(EventFile.objects.active(), pk=file_id)
  ├── permission check
  └── FileHandler(actor).soft_delete(event_file)
        ├── CommentAttachment.objects.filter(file=event_file).delete()   ← hard delete all links
        └── event_file._soft_delete(actor)                               ← mark file deleted
```

Note: `CommentAttachment` has no `deleted_at` field — it is not soft-deletable. The attachment rows are hard-deleted. This is intentional: an attachment row with a soft-deleted file is meaningless and should not persist.
