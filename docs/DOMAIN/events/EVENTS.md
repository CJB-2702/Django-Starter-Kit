# Events Domain

This document is the authoritative source of truth for the `app/events` sub-application. It covers entity design, mixin strategy, behavioural rules (shadow history, soft delete), domain scoping, and permission groups. Nothing in this module should be built without consulting this document first.

> **Asset linkage is out of scope for this build phase.** Events carry no asset reference. A future many-to-many table (event ↔ asset) will be built in `app/assets` and will reference events from that side. No asset field, import, or mention belongs in `app/events`.

---

## 0. Architectural prerequisite — Custom User Model

The project currently uses Django's default `auth.User`. Adding a `slug` field to the user (for URL identity — see §1.2) **requires a custom user model**. There is no way to add columns to `auth.User` without one.

**Action required before building events:**
1. Create a custom user model (`app/administration/models/user.py`) extending `AbstractUser`.
2. Add a `slug` field (8-char, unique, see §1.2 for generation rules).
3. Set `AUTH_USER_MODEL = "administration.User"` in `settings.py`.
4. Run a full DB reset — this is the right time to make this change since development is in progress.

All existing `ForeignKey(..., to=settings.AUTH_USER_MODEL)` references across the project will automatically point to the new model with no other changes needed.

---

## 1. Identity and URL strategy

### 1.1 Primary key rules per model

| Model | PK type | URL identity | Notes |
|---|---|---|---|
| `User` (custom) | `BigAutoField` | `slug` (8-char) | Never expose integer ID in UI or URLs |
| `Event` | `BigAutoField` | `slug` (8-char) | Never expose integer ID in UI or URLs |
| `EventComment` | `BigAutoField` | `slug` (8-char) | Never expose integer ID in UI or URLs |
| `EventFile` | UUID7 | UUID7 itself | No separate slug |
| `CommentAttachment` | UUID7 | UUID7 itself | No separate slug |

### 1.2 Slug generation

Applies to: `User`, `Event`, `EventComment`.

- **Length:** 8 characters.
- **Character set:** URL-safe base64 (`A-Z`, `a-z`, `0-9`, `-`, `_`).
- **Source:** Cryptographically random. Generated via `secrets.token_urlsafe(6)` (produces 8 URL-safe chars). Do **not** derive from the integer PK — the slug must not allow enumeration.
- **Uniqueness:** Database-level unique constraint. Retry generation on collision (collisions are statistically negligible at typical dataset sizes).
- **Immutable:** Once set, a slug never changes.
- **Generation moment:** Set in the model's `save()` method if `slug` is empty (`if not self.slug: self.slug = ...`).

---

## 2. Mixin strategy

All mixins live in `app/administration/models/`.

### 2.1 `AuditFieldsMixin` (existing — `auditable_mixin.py`)

System-level record-keeping. Applied to every events model.

| Column | Type | Behaviour |
|---|---|---|
| `created_at` | `DateTimeField(auto_now_add=True)` | Set once on insert. Never changes. |
| `updated_at` | `DateTimeField(auto_now=True)` | Updated on every `.save()`. |
| `created_by` | FK → `settings.AUTH_USER_MODEL` | User who created the row. Nullable. |
| `updated_by` | FK → `settings.AUTH_USER_MODEL` | User who last saved the row. Nullable. |

These are **system audit** fields. They record when the database row was touched, not when a real-world event occurred. **They are immutable from any application UI path.** No control layer method may allow a user to change them. Superusers who need to correct raw data must use the Django shell directly.

### 2.2 `SoftDeleteMixin` (new — create at `soft_delete_mixin.py`)

| Column | Type | Behaviour |
|---|---|---|
| `deleted_at` | `DateTimeField(null=True, blank=True)` | `None` = active. Non-null = soft-deleted at that timestamp. |

Expose `is_deleted` as a `@property` returning `self.deleted_at is not None`. All default querysets must filter `deleted_at__isnull=True`.

### 2.3 `TraceableHistoryMixin` (existing — `traceable_mixin.py`)

Extends `AuditFieldsMixin`. Applied to `EventComment` only.

| Column | Type | Behaviour |
|---|---|---|
| `origin_id` | FK → `self` | Previous revision of this row. `None` on first version. |
| `deleted_at` | `DateTimeField` | Covers soft-delete. Previous revisions always have this set. |
| `revision` | `IntegerField(default=1)` | 1-based counter. Each edit increments. |

`TraceableHistoryMixin` already includes `AuditFieldsMixin` — do not double-apply.

### 2.4 Mixin summary per model

| Model | Applied mixins |
|---|---|
| `Event` | `AuditFieldsMixin`, `SoftDeleteMixin` |
| `EventComment` | `TraceableHistoryMixin` (covers `AuditFieldsMixin` + `deleted_at`) |
| `EventFile` | `AuditFieldsMixin`, `SoftDeleteMixin` |
| `CommentAttachment` | `AuditFieldsMixin` |

---

## 3. Entities

### 3.1 `Event`

**Primary key:** `BigAutoField`. URL identity via `slug`.

**Mixins:** `AuditFieldsMixin`, `SoftDeleteMixin`

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `id` | `BigAutoField` (PK) | No | Internal. Never expose in UI. |
| `slug` | `CharField(8)` unique | No | URL identity. Random, immutable. |
| `domain` | FK → `Domain` | No | Row-level scope. `on_delete=PROTECT`. |
| `title` | `CharField(255)` | No | Short display name. |
| `description` | `TextField` | Yes | Long-form detail. |
| `event_type` | `CharField(50)` choices | No | See §3.1.1. |
| `status` | `CharField(20)` choices | No | See §3.1.2. Default: `planned`. |
| `priority` | `CharField(20)` choices | Yes | See §3.1.3. Default: `null`. |
| `event_start` | `DateTimeField` | Yes | When the real-world event started. May be past or future. Independent of `created_at`. |
| `event_end` | `DateTimeField` | Yes | When the real-world event ended. Must be ≥ `event_start` if both are set. Validated in control layer. |
| *(mixin)* `created_at` | `DateTimeField` | — | System audit. Row creation timestamp. |
| *(mixin)* `updated_at` | `DateTimeField` | — | System audit. Last save timestamp. |
| *(mixin)* `created_by` | FK → User | Yes | System audit. Immutable after creation. |
| *(mixin)* `updated_by` | FK → User | Yes | System audit. |
| *(mixin)* `deleted_at` | `DateTimeField` | Yes | `None` = active. |

#### 3.1.1 `event_type` choices

| Value | Display |
|---|---|
| `generic` | Generic |
| `system` | System |
| `administration` | Administration |
| `asset_management` | Asset Management |
| `inventory` | Inventory |
| `dispatching` | Dispatching |
| `maintenance` | Maintenance |

#### 3.1.2 `status` choices and transitions

| Value | Display | Priority-clearing? |
|---|---|---|
| `planned` | Planned | No |
| `in_progress` | In Progress | No |
| `complete` | Complete | **Yes** |
| `cancelled` | Cancelled | **Yes** |
| `failed` | Failed | **Yes** |
| `skipped` | Skipped | **Yes** |
| `blocked` | Blocked | No |

**Transitions are free** — any status may transition to any other status. No state machine enforcement. The control layer applies only the priority-clearing side-effect on transition to a clearing status.

#### 3.1.3 `priority` choices

| Value | Display |
|---|---|
| `low` | Low |
| `medium` | Medium |
| `high` | High |
| `critical` | Critical |

**Default:** `null` (no priority). The priority field is nullable; `null` is a valid and common value.

**Clearing rule:** When status transitions to `complete`, `cancelled`, `failed`, or `skipped`, `priority` is set to `null`. Enforced in the control layer write handler, not on the model.

---

### 3.2 `EventComment`

Comments are **immutable once saved**. Editing a comment creates a new revision; the old one is soft-deleted. See §4.2.

**Primary key:** `BigAutoField`. URL identity via `slug`.

**Mixins:** `TraceableHistoryMixin`

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `id` | `BigAutoField` (PK) | No | Internal. |
| `slug` | `CharField(8)` unique | No | URL identity. Random, immutable. Set on first creation; each new revision gets its own slug. |
| `event` | FK → `Event` | No | `on_delete=CASCADE`. |
| `content` | `TextField` | No | Comment body. |
| `is_human_made` | `BooleanField` | No | `True` = user-authored. `False` = machine-generated (shadow history records). Default: `True`. |
| *(mixin)* `origin_id` | FK → `self` | Yes | Previous revision. `None` on first version. |
| *(mixin)* `revision` | `IntegerField` | No | 1-based. Increments on each edit. |
| *(mixin)* `deleted_at` | `DateTimeField` | Yes | Set on previous revisions and soft-deleted comments. |
| *(mixin)* `created_at` / `updated_at` / `created_by` / `updated_by` | — | — | System audit. |

---

### 3.3 `EventFile`

Stores uploaded file metadata. File management for the events domain lives here. Other sub-apps that need file attachments import from `app/events`.

**Primary key:** UUID7. No slug.

**Mixins:** `AuditFieldsMixin`, `SoftDeleteMixin`

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `id` | UUID7 (PK) | No | |
| `file` | `FileField` | No | Django standard. Upload path: `events/files/%Y/%m/`. |
| `original_filename` | `CharField(255)` | No | Filename as uploaded. Stored separately because Django may rename on collision. |
| `file_size` | `PositiveIntegerField` | No | Bytes. Stored on upload. |
| `mime_type` | `CharField(100)` | No | MIME type from upload or extension. |
| `description` | `TextField` | Yes | Optional user description. |
| `tags` | `JSONField` | Yes | Free-form categorisation. |
| `is_technical_library` | `BooleanField` | No | Default `False`. **No logic implemented around this field yet.** Placeholder for a future routing feature. |
| *(mixin)* `created_at` / `updated_at` / `created_by` / `updated_by` | — | — | System audit. |
| *(mixin)* `deleted_at` | `DateTimeField` | Yes | Soft-delete. See §4.4. |

**Allowed extensions (enforced in control layer, not model):**

| Category | Extensions |
|---|---|
| Images | `.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`, `.webp`, `.svg` |
| Documents | `.pdf`, `.doc`, `.docx`, `.xls`, `.xlsx`, `.ppt`, `.pptx`, `.rtf` |
| Archives | `.zip`, `.rar`, `.7z`, `.tar`, `.gz` |
| Data / text | `.csv`, `.json`, `.xml`, `.sql`, `.html`, `.txt`, `.log`, `.data` |
| Code | `.cpp`, `.py`, `.java`, `.js`, `.css`, `.php` |

Maximum file size: 100 MB.

---

### 3.4 `CommentAttachment`

Join table linking an `EventComment` to an `EventFile`.

**Primary key:** UUID7. No slug.

**Mixins:** `AuditFieldsMixin`

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `id` | UUID7 (PK) | No | |
| `comment` | FK → `EventComment` | No | `on_delete=CASCADE`. |
| `file` | FK → `EventFile` | No | `on_delete=PROTECT`. The file is not deleted when an attachment link is removed. |
| `attachment_type` | `CharField(20)` choices | No | `image`, `document`, `video`. |
| `caption` | `CharField(255)` | Yes | Optional display caption. |
| `display_order` | `PositiveIntegerField` | No | Sort order within the comment. |
| *(mixin)* `created_at` / `updated_at` / `created_by` / `updated_by` | — | — | System audit. |

> Files attach to comments only in this phase. Events have no direct file attachment. To attach a file to an event, the user adds a comment and attaches the file to that comment.

---

## 4. Behavioural rules

### 4.1 Soft delete — events

1. Set `deleted_at` on the `Event` row to the current timestamp.
2. Do **not** cascade soft-delete to child comments. They remain — the historical record is preserved.
3. All standard querysets filter `deleted_at__isnull=True` by default.
4. Users with `can_view_deleted_comments_events_attachments` may call a dedicated manager method to include soft-deleted rows.

### 4.2 Shadow history — event field edits

When any content field on an `Event` is changed (title, description, event_type, status, priority, event_start, event_end), these two operations run atomically inside a transaction:

1. Create an `EventComment`:
   - `is_human_made = False`
   - `content` = JSON payload (schema below)
   - `event` = the event being edited
   - `deleted_at` = **set immediately to now** — shadow records are hidden by default
   - `revision = 1`, `origin_id = None` — shadow comments are never themselves edited

2. Update the `Event` row with the new field values.

**Shadow comment JSON schema:**
```json
{
  "changed_by": "<username>",
  "changed_at": "<ISO 8601>",
  "changes": [
    { "field": "<field_name>", "from": "<old_value>", "to": "<new_value>" }
  ]
}
```

Only fields that actually changed appear in `changes`.

Shadow comments (`is_human_made=False`) are invisible in all normal views. They are visible only to users with `can_view_deleted_comments_events_attachments`.

### 4.3 Comment edit model

Comments are never modified in place. When a user edits a comment, the following happens atomically:

1. Old comment: `deleted_at` is set to now (soft-deleted).
2. New comment is created:
   - Same `event` FK
   - `origin_id` = old comment's `id`
   - `revision` = old comment's `revision + 1`
   - `content` = new text
   - `is_human_made = True`
   - `deleted_at = None` (the new version is active)
   - New `slug` generated
3. **Attachments carry forward:** All `CommentAttachment` rows from the old comment are duplicated onto the new comment. The user can then add or remove attachments from the new revision. Old attachment links remain on the soft-deleted revision, preserving the complete historical record.

The active version in a revision chain is always the one with `deleted_at = None`.

### 4.4 File soft delete

Deleting a file means soft-deleting the `EventFile` row (setting `deleted_at`). The underlying file data on disk is **not** immediately removed — this is a soft operation.

**Permission:** Anyone who can edit the comment the file is attached to may delete that file.

**Effect on attachment links:** `CommentAttachment` rows referencing a soft-deleted `EventFile` remain in the database. The control layer must treat attachment links to soft-deleted files as broken/inaccessible and exclude them from normal display.

**What happens when a comment is soft-deleted (via edit or user delete):** The associated `EventFile` rows are also soft-deleted. If a file is attached to multiple comments and only one is soft-deleted, the file is soft-deleted only if all of its `CommentAttachment` references are to soft-deleted comments. The control layer is responsible for this check.

---

## 5. Domain scoping

| Condition | Can see the event? |
|---|---|
| User's domain set includes the event's `domain` | Yes |
| User is the `created_by` of the event | Yes — regardless of domain membership |
| Neither condition | No |

All event querysets must enforce this filter via an `EventQuerySet` manager method `visible_to(user)`:

```python
Q(domain__in=user_domains) | Q(created_by=user)
```

Deleted events are excluded from standard querysets. Users with `can_view_deleted_comments_events_attachments` may request them via a separate manager method.

---

## 6. Permissions and access control

### 6.1 Default behaviour — all authenticated users

No special permission required beyond authentication and domain membership.

| Action | Condition |
|---|---|
| Create an event | Authenticated + belongs to the target domain |
| View events | Authenticated + domain membership (or creator) |
| Add a comment | Authenticated + can see the event |
| Add attachment to own comment | Authenticated + owns the comment |
| Edit own event (triggers shadow history) | `created_by == request.user` |
| Edit own comment (revision chain) | `created_by == request.user` |
| Delete a file on own comment | `created_by == request.user` on the comment |
| Delete own event | `created_by == request.user` + no human comments (`is_human_made=True`) from other users |

**Note on the delete rule:** Shadow history comments (`is_human_made=False`) do not count as "other users' comments." Only human-authored comments (`is_human_made=True`) from users other than the event creator block self-delete.

### 6.2 Permission groups

| Group name | Grants |
|---|---|
| `default_event_permissions` | Codifies §6.1 as explicit Django permissions. Applied to all users on signup or via a default role. |
| `can_edit_others_events` | May edit content fields (title, description, event_type, status, priority, event_start, event_end) on events they did not create, within their accessible domains. Shadow history still runs. Audit fields remain immutable. |
| `can_delete_any_event` | May soft-delete any event within their domain regardless of other users' comments. |
| `can_edit_others_comments` | May edit comments they did not create (revision chain still applies). |
| `can_view_deleted_comments_events_attachments` | May query soft-deleted events, comments, attachments, and files. |

### 6.3 What permission groups do NOT do

Permission groups control **action gates** only — not data visibility. A user with `can_edit_others_events` may edit events in domains they belong to, not in domains they have no membership in. The domain filter is always enforced on top of any permission group check.

---

## 7. Out of scope for this phase

| Item | Deferred to |
|---|---|
| Asset ↔ Event many-to-many | `app/assets` (future) |
| Reply threading on comments | Future iteration |
| Audio / video file types | Left as a `# implement later` comment |
| `is_technical_library` routing logic | Placeholder column only |
| Physical file purge on soft delete | Deferred — soft delete preserves data |
