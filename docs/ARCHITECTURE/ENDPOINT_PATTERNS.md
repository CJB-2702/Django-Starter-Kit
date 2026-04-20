# Django Object-Oriented Endpoint Design Guidelines

## 1. Purpose
The goal of this document is to establish a standard for the control layer of our Django applications. While functional views are acceptable for simple data retrieval (read-only lists), we aim to leverage Object-Oriented Programming (OOP) for resource-specific entry points. This ensures better code reuse, modularity, and alignment with RESTful principles.

## 2. Core Philosophy
- **Resource-Centric:** Use Class-Based Views (CBVs) for operations tied to a specific model instance or resource lifecycle.
- **Predictable Routing:** Align URL structures with the model name and standard HTTP methods.
- **DRY (Don't Repeat Yourself):** Utilize inheritance and mixins to handle common logic like permissions, validation, and logging.

---

## 3. Implementation Standards

### 3.1. List Views (Functional Exception)
For broad entry points that aggregate data or provide complex filtering for a collection of items, functional views are permitted for simplicity.

**Path pattern:** a plural resource segment followed by a named action, with a trailing slash.

**Example path:** an events app might expose something like *events-application/view-events* for a dedicated list or dashboard screen.

The view’s job is to apply filtering, search, and pagination, then render the list template with the resulting queryset.

**Creation portals:** For screens whose purpose is to **create** a new instance of a resource (dedicated create flow, wizard, or empty form), use this path pattern explicitly: **application name** / **plural class name** / **create**, with a trailing slash unless your project standard omits it consistently.

**Example path:** *events-application/events/create* — the create portal for the Event model in the events application.

### 3.2. Plural / collection routes (OOP)
For the **collection** itself—listing items and performing **bulk** operations on many rows—Class-Based Views may be used on the plural resource path. This keeps list and bulk behavior in one place and matches REST-style collection semantics.

**Path pattern:** the plural resource with a trailing slash; the same path is used for each HTTP method below.

**Example path:** *events-application/events* (collection root).

| Method | Purpose | Request body |
| :--- | :--- | :--- |
| GET | View the list of items. Use query parameters for pagination, filters, and sort order. | None |
| DELETE | Bulk delete: remove the rows whose identifiers are named in the body. | A structured body (for example JSON) listing **which ids** to delete, in an agreed format. |
| PATCH | Bulk mutation: one logical command applied to many rows (for example assigning a set of items to a person, or changing a shared field). | A structured body with a **command** (or operation name), a **list of ids**, and the **value** (or payload) for that command. |

For PATCH bulk operations, the body should be interpreted as follows:

- **Command** — Identifies which bulk operation to run (a string or enum name agreed by the API).
- **Ids** — Primary keys or other stable identifiers for the rows to affect.
- **Value** — The new assignment, foreign key, or other payload; its shape depends on the command.

Validation, permissions, and transactional semantics (all-or-nothing versus partial success) should be implemented in the view or a service layer, not only in templates.

### 3.3. Single Resource Operations (The OOP Standard)
For viewing, creating, updating, and deleting **one** resource, **Class-Based Views (CBVs)** must be used. These views should map directly to the model name.

**Path pattern:** application prefix, singular resource name, then an id or slug segment.

**Example path:** *events-application/event* followed by a numeric primary key or slug.

#### Supported HTTP Methods:
- **GET:** Retrieve resource details.
- **POST:** Create a new resource or perform a state-changing action.
- **PUT / PATCH:** Update an existing resource. Prefer PATCH for small or partial updates (for example a single field, updating a user assignment column etc). Use PUT when the client sends most of the resource representation ex general full form updates.
- **DELETE:** Remove a resource.

### 3.4. Structural approach (example: events)
Instead of separate functional entry points for edit, delete, and show, prefer encapsulating those behaviors in class-based views: one class for the collection (list plus bulk delete and bulk patch on the plural path) and one class for a single event keyed by id.

Register routes so the collection lives at the plural path and the detail lives at the singular path plus identifier. A legacy functional list under a dedicated action name remains acceptable when it serves a specialized screen (see §3.1).

### 3.5. Child collections (nested under a parent)
When a resource **belongs to** another resource (for example comments on an event), expose the **child collection** under the parent’s detail path, then a plural segment for the child type, with a trailing slash.

**Path pattern:** application prefix, singular parent name, parent identifier, then plural child name.

**Example path:** *events-application/event* followed by an event id, then *comments* (the comments belonging to that event).

| Method | Purpose | Notes |
| :--- | :--- | :--- |
| GET | Return the **list** of child items for that parent. | Supports pagination, ordering, and filters via query parameters when needed. The parent id in the URL scopes the result; clients must not rely on omitting the parent. |
| POST | **Create** a new child item associated with that parent. | The request body carries the new child’s fields (for example text and metadata). The parent is identified **only** by the URL; the body should not substitute a different parent id, and servers should reject or ignore conflicting parent ids in the payload. |

Use class-based views for these routes so permission checks, validation, and rendering stay consistent with other OOP endpoints. Additional methods on the same child-collection path (for example bulk delete of comments) follow the same rules as §3.2 if you choose to support them there.

Operations on **one** child row (view, edit, delete a single comment) use the child detail pattern: extend the path with the child’s own id or slug after the plural segment, consistent with §3.3.

### 3.6. HTMX and partial templates (query parameters, not extra routes)
When a response must be a **partial** fragment (for example for HTMX swaps) instead of a full document, **do not** introduce parallel URL paths whose only job is to name a template variant. Keep one canonical route and branch on **query parameters** so the same resource stays one addressable endpoint. User will generally specify when to build partials.

This complements **HTMX_PATTERNS.md**: the **default** pattern there is a **full page** response with HTMX using **`hx-select`** to extract a fragment—no fragment-only response. When bandwidth or UX requires a **fragment-only** body (search, live widgets), use **this section’s** query-parameter contract on that **same** URL. The view inspects those parameters and chooses the appropriate partial or full template, reusing the same data loading and permission logic.

**Examples (illustrative only; names and values are app-defined):**

- **Search / list GET** (same path as the list or child collection): add *format=htmx-search-results* and the search query (for example *q*) — return only the results list partial; matches **HTMX_PATTERNS.md** §3.


- **Child collection GET** (same path as §3.5): add *format=htmx-focused*, *pagination=true*, *page=1*, *count=5* — return a fragment suited to HTMX, with paged rows and a chosen page size.

- **Single resource GET** (same path as §3.3 for one row, for example a comment): use the canonical detail URL for that resource and add a format query parameter — for example `events-application/comment/<id>?format=htmx-event-focused-view`, substituting the real comment id for *id*. That returns a partial such as an event-focused view of the comment, without a second route whose only purpose is that template.

Treat these query parameters as part of the public contract for each route.

For broader HTMX conventions (headers, targets, out-of-band updates, **`hx-put` / `hx-patch` / `hx-delete`** with **`CsrfViewMiddleware`** and the base-template **`htmx:configRequest`** hook, and **§6** for default **`hx-select`** on full pages vs fragment-only **`format=`** responses), see **HTMX_PATTERNS.md** in this repository.

---

## 4. Guidelines for Logic Placement

1. **Entry Points (Views):** Should be thin. Their responsibility is to parse requests, call service layers or models, and return responses.
2. **Mixins:** Use mixins for cross-cutting concerns (for example export or audit behavior) rather than duplicating code across functional views.
3. **Encapsulation:** Logic related to the state of a domain object should live on the model or in a dedicated service class, invoked by the class-based view.

## 5. Summary Table

| Feature | Entry Point Style | Example URL | Recommended Usage |
| :--- | :--- | :--- | :--- |
| Global list | Functional view | Path with plural segment and named action | Filtering, searching, dashboarding (legacy or specialized) |
| Creation portal | As agreed in §3.1 | *application-name* / *plural-class-name* / *create* | Dedicated create flow, wizard, or empty form for a new resource |
| Collection (list + bulk) | Class-based view | Plural collection root | GET for list; DELETE for bulk delete by ids; PATCH for bulk command plus ids and value |
| CRUD on one row | Class-based view | Singular resource plus id | View detail, edit, delete, update |
| Child collection | Class-based view | Parent detail path plus plural child segment | GET to list children; POST to create a child scoped to the parent |
| Single child row | Class-based view | Child collection path plus child id | View, edit, or delete one child (same ideas as §3.3) |
| Partial / HTMX fragment | Same route as the matching GET | Canonical path plus query params (for example format and pagination) | Return a partial instead of duplicating paths for template types; see §3.6 |
| State actions | Class-based view | Singular resource plus id and optional sub-path | Specialized transitions (for example cancel) |

---

## 6. Exceptions
While OOP is preferred for resource endpoints, functional views may still be used for:
- Webhooks with non-standard payloads.
- Simple redirects or static page rendering.
