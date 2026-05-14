# Event Context Design

**Status:** Draft v3 — design only, no code written.

This document covers the structs, context classes, and their interactions with existing handlers. Endpoint routing decisions live in [EVENTS_ENDPOINTS.md](EVENTS_ENDPOINTS.md). The migration from slugs to hashid-encoded integer PKs is documented in [PK_with_hashing_migration.md](PK_with_hashing_migration.md).

---

## 1. Philosophy — why these classes exist

The handlers (`EventHandler`, `CommentHandler`, `FileHandler`) each own write operations on a single model. They do not know about each other and do not manage parent-child relationships.

The context classes exist to fill that gap: **when an action has effects that cross object boundaries** (a delete cascading from event to comments to attachments to orphaned files) a context class owns the coordination. It delegates row-level work to the appropriate handler or model method but is responsible for the sequence and the cross-table decisions.

The structs exist to pre-load a complete object graph in a fixed number of queries, giving context classes and external callers all the data they need without N+1 queries.

**External callers are the primary audience.** When another application needs to work with an event — reading its full state, adding a comment, triggering a delete — these classes are the stable, single entry point that encapsulates all relational work. Within the events application itself, most single-object CRUD actions go directly to the handlers.

**Contexts do not have create() methods.** Creation is handled by a handler or factory, which produces the row. A context can be built from the result if further operations are needed. A context with no existing row to hold is undefined.

---

## 2. `_soft_delete` convention

Model classes expose `_soft_delete(actor)` as a protected method (underscore prefix). This signals that only control layer code — handlers and contexts — should call it. Presentation layer code, other models, and utilities must not call `_soft_delete` directly.

Each model's `_soft_delete()` marks only that one row as deleted. It does not cascade to children. Parent-child cascades are the context layer's job.

---

## 3. Existing infrastructure

### Models (`app/events/models/`)

| Class | PK type | Role |
|---|---|---|
| `Event` | Integer (BigAutoField) | Base event row. URL-addressed via hashid-encoded PK. |
| `EventComment` | Integer (BigAutoField) | Immutable once saved; edits produce new revisions. |
| `CommentAttachment` | UUID7 | Join record linking a comment to a file. |
| `EventFile` | UUID7 | Uploaded file record. URL-addressed by raw UUID. |

`CommentAttachment` and `EventFile` remain UUID7. All other tables use integer PKs, exposed as hashids at the URL boundary.

### Handlers (`app/events/control_layer/handlers/`)

| Class | Methods | Role |
|---|---|---|
| `EventHandler` | `create()`, `edit()` | Writes on Event rows. Shadow + machine comments on edit. |
| `CommentHandler` | `add()`, `edit()` | Writes on EventComment rows. Carries attachments forward on edit. |
| `FileHandler` | `upload()`, `soft_delete()` | `upload()` creates EventFile + CommentAttachment. `soft_delete()` hard-deletes all CommentAttachment rows referencing the file, then soft-deletes the EventFile row. |

#### Planned addition to `EventHandler`

`EventHandler._apply_machine_comment(event, message)` — creates a **visible** (not soft-deleted) machine-generated comment shown in the event timeline. Called from `edit()` when the diff contains a status change or a change to `event_start` or `event_end`.

Distinct from the existing `_apply_shadow_comment()`, which writes a full-field diff to a soft-deleted audit record invisible in the timeline.

```
edit() diff flow:
  _apply_shadow_comment()    — always; full field diff; deleted_at set at creation
  _apply_machine_comment()   — only when status, event_start, or event_end changed
```

### Presentation layer reads (`app/events/presentation_layer/`)

| Function | Role |
|---|---|
| `list_events_for_user()` | Filtered queryset for the event list view. |
| `list_comments_for_event()` | Active comments for one event (optionally including shadow). |
| `build_attachment_context()` | Iterates comments, fetches attachments — has N+1 risk, replaced by BaseEventStruct. |

`get_event_by_slug()` is removed as part of the hashids migration. Event lookup is replaced by decoding the hashid at the entrypoint then fetching by integer PK.

---

## 4. `to_dict` convention

Every struct class defines a `to_dict()` method that returns a plain `dict`. This enables templates, external callers, and debug tooling to consume the struct without depending on model internals.

Each struct defines its own `to_dict()` — no shared mixin. Nested structs call their own `to_dict()` recursively.

```
CommentStruct.to_dict() → {
  "comment_id": int,
  "content": str,
  "revision": int,
  "is_human_made": bool,
  "created_by": str,
  "created_at": str  (ISO 8601),
  "attachments": [{"attachment_id": str (uuid), "file_id": str (uuid), ...}, ...],
}

BaseEventStruct.to_dict() → {
  "event_id": int,
  "title": str,
  "status": str,
  "priority": str | None,
  "event_start": str | None,
  "event_end": str | None,
  ...other event fields...,
  "comments": [CommentStruct.to_dict(), ...],
}
```

---

## 5. `CommentStruct`

**Location:** `app/events/control_layer/domain_structs/comment_struct.py`

**Docstring the class declares:**

```
Data container for a single EventComment and its related rows.

Relationships:
  EventComment (1)
    └── CommentAttachment (0..N)  — join record
          └── EventFile (1 per attachment)
  Optionally: soft-deleted previous revisions sharing the same origin_id chain.

Example query for from_components():
  comment = EventComment.objects.select_related("created_by").get(pk=comment_id)
  attachments = list(
      CommentAttachment.objects.filter(comment_id=comment_id).select_related("file")
  )
  files = [a.file for a in attachments]
  struct = CommentStruct.from_components(comment, attachments, files)
```

### Constructor

**`CommentStruct(comment_id, include_revisions=False)`**

Required: `comment_id` — integer PK.
Optional: `include_revisions` — if True, also fetches soft-deleted previous revisions via the origin_id chain.

```
Query 1: EventComment row (select_related: created_by)
Query 2: CommentAttachment rows for this comment (select_related: file)
Query 3 (optional): Previous revision rows via origin_id chain
```

### Class method

**`CommentStruct.from_components(comment_row, attachments, files, revisions=None)`**

Accepts rows already fetched by a parent caller. Issues no DB queries. Used by `BaseEventStruct` to build child structs from a single bulk load without a per-comment round-trip.

### Fields

| Field | Type |
|---|---|
| `comment` | `EventComment` |
| `attachments` | `list[CommentAttachment]` |
| `files` | `list[EventFile]` |
| `revisions` | `list[EventComment]` — empty list if `include_revisions=False` |

### Methods

| Method | Returns |
|---|---|
| `to_dict()` | `dict` |

---

## 6. `BaseEventStruct`

**Location:** `app/events/control_layer/domain_structs/base_event_struct.py`

**Docstring the class declares:**

```
Data container for a single Event and its entire child graph.

Loads the event, all of its comments, all comment attachments, and all
referenced files in a fixed number of queries. Distributes rows to child
CommentStruct instances via from_components so no per-comment round-trip
is issued.

Relationships:
  Event (1)
    └── EventComment (0..N)
          └── CommentAttachment (0..N)
                └── EventFile (1 per attachment)

Example query for from_components():
  event = Event.objects.select_related("domain", "created_by").get(pk=event_id)
  comments = list(
      EventComment.objects.filter(event_id=event_id, deleted_at__isnull=True)
      .select_related("created_by")
  )
  comment_ids = [c.pk for c in comments]
  attachments = list(
      CommentAttachment.objects.filter(comment_id__in=comment_ids)
      .select_related("file")
  )
  files = [a.file for a in attachments]
  struct = BaseEventStruct.from_components(event, comments, attachments, files)
```

### Constructor

**`BaseEventStruct(event_id, include_shadow_comments=False)`**

Required: `event_id` — integer PK.
Optional: `include_shadow_comments` — if True, includes machine-generated shadow records alongside human comments.

```
Query 1: Event row (select_related: domain, created_by)
Query 2: EventComment rows for this event
Query 3: CommentAttachment rows for those comment IDs
Query 4: EventFile rows for those attachment IDs

Then (Python only — no further queries):
  Group attachments and files by comment ID.
  For each comment row call:
    CommentStruct.from_components(comment, attachments, files)
  Build self.comments: list[CommentStruct]
```

### Class method

**`BaseEventStruct.from_components(event_row, comment_rows, attachment_rows, file_rows)`**

Accepts fully pre-fetched row sets. Issues no DB queries. Used by `BaseEventSuperStruct` to build per-event structs from a single bulk fetch across all events.

### Fields

| Field | Type |
|---|---|
| `event` | `Event` |
| `comments` | `list[CommentStruct]` |

### Methods

| Method | Returns |
|---|---|
| `to_dict()` | `dict` — includes nested `CommentStruct.to_dict()` for each child |

---

## 7. `BaseEventSuperStruct`

**Location:** `app/events/control_layer/domain_structs/base_event_super_struct.py`

**Status:** Placeholder. No confirmed use case. Built so the pattern exists when needed.

**Docstring the class will declare:**

```
Data container for a list of Events and their complete child graphs.

Fetches all events, comments, attachments, and files in four queries across
the entire batch, then distributes rows to BaseEventStruct.from_components
for each event. Avoids the 4×N query cost of constructing BaseEventStruct
per event in a loop.

Relationships:
  Event[] (N)
    └── EventComment (0..N per event)
          └── CommentAttachment (0..N)
                └── EventFile (1 per attachment)

Example query for from_components():
  events = list(Event.objects.select_related("domain", "created_by").filter(pk__in=event_ids))
  comments = list(
      EventComment.objects.filter(event_id__in=event_ids, deleted_at__isnull=True)
      .select_related("created_by")
  )
  comment_ids = [c.pk for c in comments]
  attachments = list(
      CommentAttachment.objects.filter(comment_id__in=comment_ids).select_related("file")
  )
  files = [a.file for a in attachments]
  super_struct = BaseEventSuperStruct.from_components(events, comments, attachments, files)
```

### Constructor

**`BaseEventSuperStruct(event_ids: list[int])`**

Required: `event_ids` — list of integer PKs.

```
Query 1: All Event rows for the given IDs
Query 2: All EventComment rows for those event IDs
Query 3: All CommentAttachment rows for those comment IDs
Query 4: All EventFile rows for those attachment IDs

Then (Python only):
  Group comments, attachments, files by event ID.
  For each event call:
    BaseEventStruct.from_components(event_row, comment_rows, attachment_rows, file_rows)
  Build self.events: list[BaseEventStruct]
```

### Class method

**`BaseEventSuperStruct.from_components(event_rows, comment_rows, attachment_rows, file_rows)`**

Accepts fully pre-fetched row sets. Issues no DB queries.

### Fields

| Field | Type |
|---|---|
| `events` | `list[BaseEventStruct]` |

### Methods

| Method | Returns |
|---|---|
| `to_dict()` | `list[dict]` |

---

## 8. `CommentContext`

**Location:** `app/events/control_layer/comment_context.py`

**Role:** Stateful control object for a single comment. Owns a `CommentStruct`. Exists primarily to own the `delete()` cascade — comment deletion is not just one `_soft_delete()` call; it must also check for and clean up orphaned files.

**No `create()` method.** Adding a comment is handled by `CommentHandler.add()` or via `EventContext.add_comment()`.

### Constructors

**`CommentContext(comment_id, actor)`**

Required: `comment_id` — integer PK. Builds a `CommentStruct` internally.
Initialises `self._event = None` and `self._domain = None` for lazy loading.

**`CommentContext.create_from_struct(comment_struct, actor)`**

Accepts a pre-built `CommentStruct`. Zero extra queries. Used by `EventContext` when it already holds all child comment structs from its `BaseEventStruct`.
Also initialises `self._event = None` and `self._domain = None`.

### Internal state

| Attribute | Initial value | Set by |
|---|---|---|
| `self.struct` | `CommentStruct` | constructor |
| `self.actor` | user | constructor |
| `self._event` | `None` | `event` property on first access |
| `self._domain` | `None` | `domain` property on first access |

### Properties

**`event`** — lazy-loaded `Event` row for this comment.

```python
@property
def event(self):
    if self._event is None:
        self._event = Event.objects.select_related("domain").get(
            pk=self.struct.comment.event_id
        )
    return self._event
```

Useful for permission checks in entrypoints that have a `CommentContext` but have not separately fetched the parent event.

**`domain`** — lazy-loaded `Domain` row via `self.event`.

```python
@property
def domain(self):
    if self._domain is None:
        self._domain = self.event.domain
    return self._domain
```

If `event` was already loaded (e.g. via the `event` property above), `domain` costs zero additional queries because `select_related("domain")` was used in the `event` property query.

### Methods

| Method | Delegates to | Notes |
|---|---|---|
| `edit(post_data)` | `CommentHandler.edit(self.struct.comment, post_data)` | Thin wrapper |
| `delete()` | See below | Owns the attachment/file cascade |

### `delete()` — cascade detail

```
CommentContext.delete():
  1. self.struct.comment._soft_delete(actor=self.actor)

  2. For each attachment in self.struct.attachments:
       other_refs = CommentAttachment.objects.filter(
           file_id=attachment.file_id
       ).exclude(comment_id=self.struct.comment.pk).exists()

       if not other_refs:
           FileHandler(self.actor).soft_delete(attachment.file)
             → hard-deletes all CommentAttachment rows for that file
             → soft-deletes the EventFile row
```

The `other_refs` check matters because `CommentHandler.edit()` carries attachment rows forward to new revisions. A file may be referenced by multiple revisions; it is only soft-deleted when no other attachment row still points to it.

---

## 9. `EventContext`

**Location:** `app/events/control_layer/event_context.py`

**Role:** Stateful control object for a single event. Owns a `BaseEventStruct`. Primary entry point for external callers who need to work with an event. Coordinates cross-table write operations; delegates single-row writes to the handlers.

**No `create()` method.** Event creation is handled by `EventHandler.create()`, which returns the new row. If a context is needed after creation: `EventContext(result.event.id, actor)`.

### Constructors

**`EventContext(event_id, actor)`**

Required: `event_id` — integer PK. Builds a `BaseEventStruct` internally.

**`EventContext.create_from_struct(base_event_struct, actor)`**

Accepts a pre-built `BaseEventStruct`. Zero extra queries. Used when the caller has already paid for the query.

### Methods

| Method | Delegates to | Notes |
|---|---|---|
| `edit(post_data)` | `EventHandler.edit(self.struct.event, post_data)` | Thin wrapper |
| `add_comment(post_data)` | `CommentHandler.add(self.struct.event, post_data)` | Provides the event; caller doesn't need to pass it |
| `add_attachment(uploaded_file)` | See below | Creates machine comment + attaches file |
| `delete()` | See below | Owns the full cascade |

### `add_attachment()` — detail

Attaches a file directly to the event by creating a visible machine-generated comment as the attachment carrier. The file appears in the event timeline without requiring a human comment thread.

```
EventContext.add_attachment(uploaded_file):
  1. Create EventComment:
       event=self.struct.event
       content=f"File added: {uploaded_file.name}"
       is_human_made=False
       deleted_at=None          ← visible in the timeline
       created_by=self.actor

  2. FileHandler(self.actor).upload(machine_comment, uploaded_file)
       → creates EventFile
       → creates CommentAttachment linking the machine comment to the file
```

### `delete()` — cascade detail

`EventContext.delete()` does not import or directly touch comment, attachment, or file models. All child cleanup is delegated to `CommentContext`, which owns those relationships.

```
EventContext.delete():
  1. self.struct.event._soft_delete(actor=self.actor)

  2. For each comment_struct in self.struct.comments:
       CommentContext.create_from_struct(comment_struct, self.actor).delete()
         → comment._soft_delete(actor)
         → orphaned files soft-deleted
```

`create_from_struct` is zero-cost here — `BaseEventStruct` already holds all comment data; no queries are issued during `CommentContext` construction in this path.

---

## 10. ID boundary — hashids at the URL layer

All URLs that reference an event or comment expose a hashid-encoded integer PK. Internally, the control layer always works with integer PKs and model instances — never with hashids or slugs.

```
URL /events/Yz3kP9m2/
  → entrypoint decodes "Yz3kP9m2" → event_id (int)
  → get_object_or_404(Event.objects.active(), pk=event_id)
  → EventContext(event_id, actor)
```

The encoding/decoding utility lives in `app/utils/hashids.py`. Only entrypoints call it. Nothing inside the control layer or struct layer is aware of hashids.

See [PK_with_hashing_migration.md](PK_with_hashing_migration.md) for full migration details.

---

## 11. File locations

```
app/events/control_layer/
  domain_structs/
    __init__.py
    comment_struct.py            ← CommentStruct
    base_event_struct.py         ← BaseEventStruct
    base_event_super_struct.py   ← BaseEventSuperStruct (placeholder)
  event_context.py               ← EventContext
  comment_context.py             ← CommentContext
  handlers/
    event_handler.py             ← add _apply_machine_comment()
    comment_handler.py           ← no changes
    file_handler.py              ← no changes

app/utils/
  hashids.py                     ← encode_id() / decode_hash() utility
```
