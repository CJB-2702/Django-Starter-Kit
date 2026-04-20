# Layered architecture rules (reads vs writes)

This document tightens how **`presentation_layer/entrypoints`** (HTTP endpoints) and the rest of the presentation layer interact with the database. It complements the project overview in `ARCHITECTURE.md`.

## Writes: control layer only

The presentation layer and endpoints **must not persist changes**. All mutations go through the **control layer** (write orchestration modules, adapters, and any shared helpers those call).

| Operation | Where it may run |
| :--- | :--- |
| **Create** rows (`.create()`, bulk create, `get_or_create` that inserts, etc.) | **Control layer only** — not in `presentation_layer/entrypoints` or other presentation code. |
| **Update** rows (`.save()`, `.update()`, `bulk_update`, m2m `.add()` / `.remove()`, etc.) | **Control layer only**. |
| **Delete** rows (`.delete()`, queryset delete, clearing relations that remove rows, etc.) | **Control layer only**. |

**Rationale:** Endpoints stay thin “traffic controllers”: they validate the HTTP surface, call **search** for reads (when needed), call **control layer** for mutations, then return a response. That keeps one place to audit business rules and side effects for state changes.

## Reads: allowed in endpoints with limits

**Viewing** data is allowed inside entrypoints using ORM queries, **when the read stays simple**.

### Simple reads (OK in the endpoint)

You may query and assemble context **directly in the entrypoint** (or via a tiny local helper used only by that endpoint) when **at most two logical tables** are involved in serving the page or fragment — for example:

- One primary row plus one related collection loaded in an obvious way (e.g. `select_related` / `prefetch_related` on a single hop).
- Typical case: an **event** and its **comments** for a read-only detail or list row.

**Example (conceptual):** a GET handler loads `Event` with `prefetch_related("comments")`, builds a template context, returns `render(...)`. No maintenance actions, attachments, parts, or other subgraphs.

### Complex reads (not inlined in the endpoint)

If the screen needs data that spans **more than two tables** (or more than two coherent ORM relations) — e.g. comments **and** attachments **and** actions **and** headers **and** parts — **do not** grow a large query chain inside the entrypoint.

Use one of:

1. **`presentation_layer/search/`** — a named function (or small module) that encapsulates the filters, annotations, and `select_related` / `prefetch_related` strategy; the entrypoint calls that function and renders.
2. **`control_layer/domain_structs/`** — a typed aggregate (e.g. dataclass) plus a **loader** (in search or next to the struct, per `ARCHITECTURE.md`) that, given a natural key such as an event id, **eager-loads or prefetches** every business-related row the UI needs so the template receives one coherent object graph.

**Example (conceptual):** a **maintenance event** detail needs comments, attachments, actions, line headers, parts, etc. Define something like `MaintenanceEventDetail` in `domain_structs/`, and a loader `MaintenanceEventDetail(event_id)` that performs all prefetching in one place and builds an accessable dataclass. The entrypoint creates the object `MaintenanceEventDetail(...).as_dict()` and passes the struct into the template.

**Rule of thumb:** if you need to mentally track **more than two** tables (or two hops of relations) to explain what the endpoint is loading, move the read behind **search** or a **domain struct** loader.

## Quick reference

| Question | Answer |
| :--- | :--- |
| May an endpoint create/update/delete rows? | **No** — delegate to the **control layer**. |
| May an endpoint run SELECTs for a simple 1–2 table view? | **Yes** — direct queries in the entrypoint are fine. |
| May an endpoint embed a large multi-table load? | **No** — use **`presentation_layer/search/`** or a **`domain_struct`** with prefetch/eager load. |
| Where do aggregates for complex screens live? | **`control_layer/domain_structs/`** (types); construction often in **search** or control code per `ARCHITECTURE.md`. |

## Examples

### Allowed: thin read in the endpoint

- **Use case:** Read-only list of events with comment counts for a dashboard fragment.
- **OK:** Entrypoint calls `Event.objects.filter(...).annotate(comment_count=Count("comments"))` or delegates one small `search.events_for_dashboard()` that only touches the event + comment relationship. Still **no writes** in the entrypoint.

### Allowed: simple event + comments detail

- **Use case:** Event detail page showing the event row and its comments.
- **OK:** `Event.objects.prefetch_related("comments").get(pk=...)` in the entrypoint or a one-function search helper. Two main concerns (event + comments). **Creates** for new comments still go through **control layer** (e.g. POST handler calls `control_layer.comments.add_comment(...)`).

### Not allowed: fat query in the endpoint

- **Use case:** Maintenance event screen with comments, attachments, actions, headers, parts, assignees, etc.
- **Avoid:** Fifty lines of ORM in `entrypoints/maintenance_event_detail.py`.
- **Do instead:** `MaintenanceEventDetail = load_maintenance_event_detail(event_id)` implemented in `presentation_layer/search/maintenance_events.py` (or a loader paired with `domain_structs/maintenance_event_detail.py`) with all `prefetch_related` / `select_related` spelled out once.

### Writes always via control layer

- **Use case:** User submits a form to add a comment.
- **Endpoint:** Parses POST, then calls e.g. `control_layer.comments.add_comment(event_id=..., body=..., user=...)`.
- **Not allowed:** `Comment.objects.create(...)` inside the entrypoint.

---

These rules are intentionally strict on **writes** and pragmatic on **reads**, so simple pages stay easy to write while complex aggregates stay maintainable and testable in **search** and **domain structs**.
