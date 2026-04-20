# Legacy core models (`core_model_old_project`)

This document inventories **SQLAlchemy** models copied from the previous Flask application’s `core` data layer (`core_model_old_project/`). Table names come from each model’s `__tablename__` (or the `UserCreatedBase` naming rule where noted).

**Shared audit columns** — Models inheriting `UserCreatedBase` include:

| Column | Type (SQLAlchemy) | FK |
| --- | --- | --- |
| `id` | Integer, PK | — |
| `created_at` | DateTime | — |
| `created_by_id` | Integer, nullable | → `users.id` |
| `updated_at` | DateTime | — |
| `updated_by_id` | Integer, nullable | → `users.id` |

Unless a table is listed as an exception, assume these five columns plus the table-specific columns below.

---

## `users`

Standalone user account (not using `UserCreatedBase`).

| Column | Type | Notes |
| --- | --- | --- |
| `id` | Integer, PK | |
| `username` | String(80), unique | |
| `email` | String(120), unique | |
| `password_hash` | String(255) | |
| `is_active` | Boolean | |
| `is_system` | Boolean | |
| `created_at` | DateTime | |
| `updated_at` | DateTime | |
| `password_changed_at` | DateTime | |
| `last_password_change_notification` | DateTime, nullable | |
| `failed_login_attempts` | Integer | |
| `locked_until` | DateTime, nullable | |

**Foreign keys:** none.

---

## `password_history`

| Column | Type | Notes |
| --- | --- | --- |
| `id` | Integer, PK | |
| `user_id` | Integer, not null | → `users.id` |
| `password_hash` | String(255) | |
| `created_at` | DateTime, not null | |

**Foreign keys:** `user_id` → `users.id`.

---

## `portal_user_data`

Inherits `UserCreatedBase` (audit columns as above).

| Column | Type | Notes |
| --- | --- | --- |
| `user_id` | Integer, not null, unique | → `users.id` |
| `quicklinks` | JSON | default list |
| `general_settings` | JSON | |
| `core_settings` | JSON | |
| `maintenance_settings` | JSON | |
| `general_cache` | JSON | |
| `core_cache` | JSON | |
| `maintenance_cache` | JSON | |

**Foreign keys:** `user_id` → `users.id`; `created_by_id`, `updated_by_id` → `users.id`.

---

## `major_locations`

Inherits `UserCreatedBase`.

| Column | Type | Notes |
| --- | --- | --- |
| `name` | String(100), not null | |
| `description` | Text, nullable | |
| `address` | Text, nullable | |
| `is_active` | Boolean | |

**Foreign keys:** `created_by_id`, `updated_by_id` → `users.id`.

---

## `asset_classes`

Inherits `UserCreatedBase`.

| Column | Type | Notes |
| --- | --- | --- |
| `name` | String(100), not null | |
| `description` | Text, nullable | |
| `category` | String(100), nullable | |
| `is_active` | Boolean | |

**Foreign keys:** `created_by_id`, `updated_by_id` → `users.id`.

---

## `make_models`

Inherits `UserCreatedBase`.

| Column | Type | Notes |
| --- | --- | --- |
| `make` | String(100), not null | |
| `model` | String(100), not null | |
| `year` | Integer, nullable | |
| `revision` | String(100), nullable | |
| `description` | Text, nullable | |
| `is_active` | Boolean | |
| `asset_class_id` | Integer, not null | → `asset_classes.id` |
| `meter1_unit` … `meter4_unit` | String(100), nullable | |

**Foreign keys:** `asset_class_id` → `asset_classes.id`; `created_by_id`, `updated_by_id` → `users.id`.

---

## `assets`

Inherits `UserCreatedBase`.

| Column | Type | Notes |
| --- | --- | --- |
| `name` | String(100), not null | |
| `serial_number` | String(100), unique, not null | |
| `status` | String(50) | |
| `capability_status` | String(20), nullable | |
| `major_location_id` | Integer, nullable | → `major_locations.id` |
| `make_model_id` | Integer, not null | → `make_models.id` |
| `asset_class_id` | Integer, not null | → `asset_classes.id` |
| `meter1` … `meter4` | Float, nullable | |
| `tags` | JSON, nullable | |
| `detail_rows_created` | JSON, nullable | |
| `root_asset_id` | Integer, nullable | → `assets.id` (self) |
| `parent_asset_id` | Integer, nullable | → `assets.id` (self) |
| `depth_from_root` | Integer, nullable | |
| `is_active` | Boolean | |

**Foreign keys:** `major_location_id` → `major_locations.id`; `make_model_id` → `make_models.id`; `asset_class_id` → `asset_classes.id`; `root_asset_id`, `parent_asset_id` → `assets.id`; `created_by_id`, `updated_by_id` → `users.id`.

---

## `attachments`

Inherits `UserCreatedBase`.

| Column | Type | Notes |
| --- | --- | --- |
| `filename` | String(255), not null | |
| `file_size` | Integer, not null | bytes |
| `mime_type` | String(100), not null | |
| `description` | Text, nullable | |
| `tags` | JSON, nullable | |
| `is_technical_library` | Boolean, not null | default false |
| `storage_type` | String(20), not null | e.g. `database` / `filesystem` |
| `file_path` | String(500), nullable | |
| `file_data` | LargeBinary, nullable | |

**Foreign keys:** `created_by_id`, `updated_by_id` → `users.id`.

---

## `asset_images`

Concrete subclass of abstract `VirtualAttachmentReference` (which subclasses `UserCreatedBase`). Columns = audit + virtual reference fields + asset-specific.

| Column | Type | Notes |
| --- | --- | --- |
| *(audit)* | | `UserCreatedBase` |
| `attachment_id` | Integer, not null | → `attachments.id` |
| `all_attachment_references_id` | Integer, not null | global sequence (see below) |
| `attached_to_id` | Integer, not null | → `assets.id` |
| `attached_to_type` | String(20), not null | e.g. `Asset` |
| `display_order` | Integer, not null | |
| `attachment_type` | String(20), not null | e.g. Image/Document/Video |
| `caption` | String(255), nullable | |
| `is_primary` | Boolean, not null | default false |

**Foreign keys:** `attachment_id` → `attachments.id`; `attached_to_id` → `assets.id`; `created_by_id`, `updated_by_id` → `users.id`.

---

## `comment_attachments`

Same virtual-reference pattern as `asset_images`, for comments.

| Column | Type | Notes |
| --- | --- | --- |
| *(audit)* | | `UserCreatedBase` |
| `attachment_id` | Integer, not null | → `attachments.id` |
| `all_attachment_references_id` | Integer, not null | |
| `attached_to_id` | Integer, not null | → `comments.id` |
| `attached_to_type` | String(20), not null | e.g. `Comment` |
| `display_order` | Integer, not null | |
| `attachment_type` | String(20), not null | |
| `caption` | String(255), nullable | |

**Foreign keys:** `attachment_id` → `attachments.id`; `attached_to_id` → `comments.id`; `created_by_id`, `updated_by_id` → `users.id`.

---

## `comments`

Inherits `UserCreatedBase`.

| Column | Type | Notes |
| --- | --- | --- |
| `content` | Text, not null | |
| `event_id` | Integer, not null | → `events.id` |
| `is_human_made` | Boolean | |
| `user_viewable` | String(20), nullable | |
| `previous_comment_id` | Integer, nullable | → `comments.id` |
| `replied_to_comment_id` | Integer, nullable | → `comments.id` |

**Foreign keys:** `event_id` → `events.id`; `previous_comment_id`, `replied_to_comment_id` → `comments.id`; `created_by_id`, `updated_by_id` → `users.id`.

---

## `events`

Inherits `UserCreatedBase`.

| Column | Type | Notes |
| --- | --- | --- |
| `event_type` | String(100), not null | |
| `description` | Text, not null | |
| `timestamp` | DateTime | |
| `user_id` | Integer, nullable | → `users.id` |
| `asset_id` | Integer, nullable | → `assets.id` |
| `major_location_id` | Integer, nullable | → `major_locations.id` |
| `status` | String(20), nullable | |

**Foreign keys:** `user_id` → `users.id`; `asset_id` → `assets.id`; `major_location_id` → `major_locations.id`; `created_by_id`, `updated_by_id` → `users.id`.

---

## `meter_history`

Inherits `UserCreatedBase`.

| Column | Type | Notes |
| --- | --- | --- |
| `asset_id` | Integer, not null | → `assets.id` |
| `meter1` … `meter4` | Float, nullable | |
| `recorded_at` | DateTime, not null | |
| `recorded_by_id` | Integer, nullable | → `users.id` |

**Foreign keys:** `asset_id` → `assets.id`; `recorded_by_id` → `users.id`; `created_by_id`, `updated_by_id` → `users.id`.

*Indexes (metadata):* `idx_meter_history_asset_id` on `asset_id`; `idx_meter_history_recorded_at` on `recorded_at`.

---

## `roles_system`

Dictionary table; not using `UserCreatedBase`.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | Integer, PK | |
| `key` | String(80), unique, not null | |
| `label` | String(120), not null | |
| `priority` | Integer, not null | |
| `description` | Text, nullable | |

**Foreign keys:** none.

---

## `roles_modules`

| Column | Type | Notes |
| --- | --- | --- |
| `id` | Integer, PK | |
| `module_key` | String(80), not null | |
| `role_key` | String(120), not null | |
| `label` | String(120), not null | |
| `description` | Text, nullable | |

**Foreign keys:** none.

---

## `user_system_roles`

| Column | Type | Notes |
| --- | --- | --- |
| `id` | Integer, PK | |
| `user_id` | Integer, not null | → `users.id` |
| `role_id` | Integer, not null | → `roles_system.id` |
| `granted_by_id` | Integer, nullable | → `users.id` |
| `granted_at` | DateTime, not null | |

**Foreign keys:** `user_id`, `granted_by_id` → `users.id`; `role_id` → `roles_system.id`.

---

## `user_module_roles`

| Column | Type | Notes |
| --- | --- | --- |
| `id` | Integer, PK | |
| `user_id` | Integer, not null | → `users.id` |
| `module_role_id` | Integer, not null | → `roles_modules.id` |
| `granted_by_id` | Integer, nullable | → `users.id` |
| `granted_at` | DateTime, not null | |

**Foreign keys:** `user_id`, `granted_by_id` → `users.id`; `module_role_id` → `roles_modules.id`.

---

## `user_major_location_access`

| Column | Type | Notes |
| --- | --- | --- |
| `id` | Integer, PK | |
| `user_id` | Integer, not null | → `users.id` |
| `location_id` | Integer, not null | → `major_locations.id` |
| `granted_by_id` | Integer, nullable | → `users.id` |
| `granted_at` | DateTime, not null | |

**Foreign keys:** `user_id`, `granted_by_id` → `users.id`; `location_id` → `major_locations.id`.

---

## `user_asset_class_access`

| Column | Type | Notes |
| --- | --- | --- |
| `id` | Integer, PK | |
| `user_id` | Integer, not null | → `users.id` |
| `location_id` | Integer, not null | → `major_locations.id` |
| `asset_class_id` | Integer, not null | → `asset_classes.id` |
| `granted_by_id` | Integer, nullable | → `users.id` |
| `granted_at` | DateTime, not null | |

**Foreign keys:** `user_id`, `granted_by_id` → `users.id`; `location_id` → `major_locations.id`; `asset_class_id` → `asset_classes.id`.

---

## `parts` (`PartDefinition`)

Inherits `UserCreatedBase`. Catalog part definition; table name is `parts`.

| Column | Type | Notes |
| --- | --- | --- |
| `part_number` | String(100), unique, not null | |
| `part_name` | String(200), not null | |
| `description` | Text, nullable | |
| `category` | String(100), nullable | |
| `manufacturer` | String(200), nullable | |
| `supplier` | String(200), nullable | |
| `revision` | String(50), nullable | |
| `last_unit_cost` | Float, nullable | |
| `unit_of_measure` | String(50), nullable | |
| `location` | String(200), nullable | |
| `status` | String(20) | e.g. Active/Inactive |

**Foreign keys:** `created_by_id`, `updated_by_id` → `users.id`.

*Note:* The model references a `PartDemand` relationship in code that lives outside this folder; that table is not defined in `core_model_old_project/`.

---

## `tools` (`ToolDefinition`)

Inherits `UserCreatedBase`.

| Column | Type | Notes |
| --- | --- | --- |
| `tool_name` | String(200), not null | |
| `description` | Text, nullable | |
| `tool_type` | String(100), nullable | |
| `manufacturer` | String(200), nullable | |
| `model_number` | String(100), nullable | |

**Foreign keys:** `created_by_id`, `updated_by_id` → `users.id`.

---

## Sequence counter tables (infrastructure)

Created by `VirtualSequenceGenerator` / ID managers for global IDs:

| Table | Columns | Foreign keys |
| --- | --- | --- |
| `_sequence_attachment_id` | `id` (PK), `current_value` | none |
| `_sequence_event_detail_id` | `id` (PK), `current_value` | none |

These back `all_attachment_references_id` on virtual attachment rows and `all_details_id` on concrete `EventDetailVirtual` subclasses (defined outside this package).

---

## Abstract bases (no table)

| Name | Role |
| --- | --- |
| `UserCreatedBase` | Adds audit columns; default name would be `{class}s` if not overridden |
| `VirtualAttachmentReference` | Shared columns for `asset_images` and `comment_attachments` |
| `EventDetailVirtual` | Shared columns for event-detail rows: `event_id` → `events.id`, `all_details_id`, `asset_id` → `assets.id`, plus audit via `UserCreatedBase` |

---

## Summary: tables in `core_model_old_project`

| Table |
| --- |
| `_sequence_attachment_id` |
| `_sequence_event_detail_id` |
| `asset_classes` |
| `asset_images` |
| `assets` |
| `attachments` |
| `comment_attachments` |
| `comments` |
| `events` |
| `major_locations` |
| `make_models` |
| `meter_history` |
| `parts` |
| `password_history` |
| `portal_user_data` |
| `roles_modules` |
| `roles_system` |
| `tools` |
| `user_asset_class_access` |
| `user_major_location_access` |
| `user_module_roles` |
| `user_system_roles` |
| `users` |
