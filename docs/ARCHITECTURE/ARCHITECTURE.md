# Project Architecture Specification

**Extra-Explicit Modular Django Design**

## 1. Overview

This document defines the “Extra-Explicit” layout for Django apps in this project. HTTP handling, business logic, data access, and presentation-oriented shaping are split into dedicated layers so behavior stays easy to find and change.

The end state is **six major sub-applications** (Django apps), each owning roughly **six micro-applications**—cohesive feature slices that usually center on a **model** or **domain struct** and live *inside* one sub-application’s codebase and template tree, not as separate `INSTALLED_APPS` unless you deliberately split them.

Standard Django files (`migrations/`, `apps.py`, `admin.py`, `management/commands/`, optional `templatetags/`) are treated as **configuration** or **infrastructure** and kept separate from the **business/logic** layers below.

## 2. Folder Structure

Each sub-application follows this tree. Comments describe role, not folder names.

```text
<sub-application>/
├── migrations/            # Auto-generated DB history (app root; do not relocate)
├── management/            # Custom manage.py commands
│   └── commands/
├── apps.py                # AppConfig; use ready() for wiring (e.g. signals)
├── admin.py               # Django Admin registration (thin; may call control_layer)
├── urls.py                # Maps paths to entrypoint callables (GET/POST/PUT/PATCH/DELETE/…)
├── presentation_layer/    # User-facing surfaces and read-side helpers used by those surfaces
│   ├── entrypoints/       # All HTTP endpoints: thin handlers; delegate to control_layer / search
│   ├── search/            # QuerySets: filter, exclude, annotate beyond one-liners
│   └── tools/             # Utilities, external APIs, shared helpers (e.g. signals)
├── control_layer/         # State changes and shared domain shaping for writes
│   ├── adapters/          # POST cleanup, DTOs, template-ready shaping (often before/after writes)
│   ├── domain_structs/    # Aggregates: related model data grouped for layers above ORM
│   └── …                  # Write orchestration modules (create/update/delete flows)
├── models/                # Schema and constraints (package, not a single file)
└── templates/             # See “Template layout” below (sub-app vs micro-application)
```

**`control_layer/domain_structs/`** holds typed bundles used by entrypoints, search, adapters, and write modules—not the ORM models themselves, but composites built from them. Example: given an event id, a struct might carry the event header, its line items, and related comments so every layer above `models/` passes one coherent object instead of juggling loose querysets.

**`control_layer/`** (excluding `adapters/` and `domain_structs/`) is where write orchestration lives: explicit modules that create, update, or delete persisted state. The old name “controllers” maps to this package as a whole; individual Python modules sit beside `adapters/` and `domain_structs/`.

### Template layout (sub-application vs micro-application)

Django still loads templates from this app’s `templates/` directory; within it, distinguish **sub-application** (whole Django app) surfaces from **micro-application** (feature slice) surfaces.

**Sub-application templates** — pages and partials that belong to the sub-app as a whole, not to one micro-feature folder. Name them with a **short prefix** derived from the sub-application (same idea as the app label), then an underscore, then the template role:

```text
<sub-application>/templates/<prefix>_<name>.html
```

Examples for a sub-application `events-application` with prefix `ea`:

- `events-application/templates/ea_index.html`
- `events-application/templates/ea_dashboard.html`

Use one consistent prefix per sub-application so filenames stay unique and grep-friendly.

**Micro-application templates** — feature slices (micro-applications) and their **fragments** are usually tied to a **specific model** or **domain struct** (aggregate). Name the subdirectory after that primary type so the template namespace matches the data it represents. Use a filesystem-friendly form of the model or struct name (typically **snake_case** from the Django model class, e.g. `Comment` → `comment/`).

```text
<sub-application>/templates/<model_or_struct_namespace>/<name>.html
```

Examples (assuming models `Comment` and `EventLine`):

- `events-application/templates/comment/add_comment_page.html`
- `events-application/templates/comment/fragments/comment_row.html` — HTMX partials for that model’s UI

If a slice is centered on a **domain struct** rather than one table, use the struct’s name the same way (e.g. `event_detail/` for templates built around an `EventDetail` aggregate).

Sub-application–wide HTMX partials that are not tied to one model or struct may stay as `templates/<prefix>_…` or a small shared subtree you document for that app—pick one convention per sub-application and stick to it.

When rendering, use the path relative to `templates/` (e.g. `ea_dashboard.html`, `comment/add_comment_page.html`).

Optional: `templatetags/` only if unavoidable; prefer preparing data in entrypoints, `presentation_layer/search`, or `control_layer/adapters` before render.

Django’s own docs call these callables **views**; this project keeps them under `presentation_layer/entrypoints/` so it is obvious that every file here is an HTTP-facing endpoint.

## 3. Layer Responsibilities

| Layer | Primary goal | Allowed imports |
| :--- | :--- | :--- |
| **Presentation / entrypoints** | All HTTP methods (GET, POST, PUT, PATCH, DELETE, …): parse requests, call search or control layer, return responses. | `control_layer`, `presentation_layer/search`, `presentation_layer/tools`, `models` |
| **Presentation / search** | Encapsulate complex read/query logic; often assemble `domain_structs` from querysets. | `models`, `control_layer/domain_structs` |
| **Presentation / tools** | Cross-cutting helpers (signals, integrations) used by entrypoints or app startup. | `models`, `control_layer`, `presentation_layer/search` (sparingly; avoid cycles) |
| **Control / adapters** | Transform data for UI or downstream use; clean input before writes. | `models`, `presentation_layer/search`, `control_layer/domain_structs` |
| **Control layer (writes)** | Orchestrate writes (create/update/delete flows). | `models`, `presentation_layer/search`, `control_layer/domain_structs` |
| **Control / domain structs** | Typed aggregates of related model data (graphs, nested bundles). | `models` |
| **Models** | Schema and integrity rules. | None above the ORM/base layer |

**Golden rule:** Dependencies flow *downward*. A model must not import the control layer or a domain struct. Search must not import an entrypoint.

## 4. Implementation Patterns

### Adapter pattern

Code in `control_layer/adapters/` cleans `request.POST` (or similar) before a write runs, or shapes model instances into template contexts.

### Search pattern

Any `.filter()`, `.exclude()`, or `.annotate()` chain longer than one line belongs in `presentation_layer/search/` so entrypoints stay thin “traffic controllers.”

### Domain structs pattern

Keep aggregate **types** (dataclasses, `NamedTuple`, or similar) in `control_layer/domain_structs/`. Prefer constructing instances in `presentation_layer/search` or in control-layer write modules so `domain_structs/` stays mostly declarative and does not need to import `presentation_layer/search` (avoids awkward cycles). If a factory must live next to the type, a submodule may import search—keep that edge rare and one-directional.

Example: an `EventDetail` struct holds an event row, its items, and its comments; `presentation_layer/search` loads the rows and returns `EventDetail` for entrypoints and adapters to use.

### Writes vs reads

- **Control layer** changes system state (writes) and holds adapters plus domain aggregates used by those flows.
- **Presentation / search** answers questions about state (reads).

If a flow needs both, the entrypoint calls search then the control layer (or the reverse), instead of mixing read and write in one place.

### HTMX fragments

Templates used only as HTMX responses (table rows, modals, inline form errors, etc.) should not sit beside unrelated full-page templates. Prefer **`templates/<model_or_struct_namespace>/fragments/`** so partials stay next to the same model or struct as the full pages for that slice. Use a sub-application–level fragment only when the swap is truly cross-cutting. See `docs/HTMX_PATTERNS.md` for request/response conventions.

## 5. Django “plumbing” files

### `migrations/`

Tracks schema history. Stays at the app root; `makemigrations` expects it there even when `models/` is a package. Do not move manually.

### `apps.py`

Holds `AppConfig` and is the right place for app startup. For signals, import from something like `presentation_layer/tools/signals.py` inside `ready()`.

### `admin.py`

Registers models with Django Admin. Treat it like a specialized admin-facing surface: import from `models/` and, for actions, `control_layer`. Splitting into an `admin/` package is optional.

### `management/commands/`

Custom CLI (e.g. `python manage.py cleanup_data`). Same discipline as HTTP entrypoints: parse arguments, then delegate to **control layer** or **presentation_layer/search**.

### `templatetags/`

Avoid when possible; build context in entrypoints, search, or adapters. If you must use tags, keep them thin and call into `control_layer/adapters/` rather than embedding logic in templates.

## 6. Adding a New Application

1. Create the app: `python manage.py startapp [app_name]`.
2. Remove the default `views.py` and `models.py` files.
3. Create directories: `presentation_layer`, `presentation_layer/entrypoints`, `presentation_layer/search`, `presentation_layer/tools`, `control_layer`, `control_layer/adapters`, `control_layer/domain_structs`, `models`, plus `templates/`. Add `templates/<prefix>_<name>.html` for sub-application pages and `templates/<model_or_struct_namespace>/` (with optional `fragments/`) per feature slice as features appear.
4. Add `__init__.py` where required so packages resolve.
5. Register the app in `config/settings.py`.
6. Add the app’s root `urls.py`: import HTTP handlers from `presentation_layer.entrypoints` (not a `views.py` at app root) and wire `urlpatterns` to those callables.
7. Include the app’s URLs from the project `urls.py`.

## 7. Import flow for infrastructure

| From | Typical imports |
| :--- | :--- |
| `admin.py` | `models/`, sometimes `control_layer/` |
| `management/commands/` | `presentation_layer/search`, `control_layer/` |
| `templatetags/` (if used) | `control_layer/adapters/` |
| `migrations/` | Generated from `models/`; do not hand-edit except in exceptional cases |

Together, sections 2–3 define layout and dependency rules; sections 4–5 spell out patterns and where Django’s built-in hooks live; sections 6–7 cover bootstrapping apps and how CLI/admin entry points mirror the same “thin handler” rule as HTTP entrypoints.
