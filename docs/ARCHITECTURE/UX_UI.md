# UX and UI (Bulma)

**Glossary**

- **Portal** — A **distinct product area** with its own purpose, entry points, and navigation (for example **Event management** vs **Restocking**). Portals stay separate from each other; they are not “steps” of the same task.
- **Guided flow** — The **steps of one task** (for example creating an event) modeled on **one URL** as a single scrolling page: later steps are **visible but disabled** until earlier steps validate. Contrast with splitting the same task across `/create/step-1`, `/create/step-2`, which we avoid for that use case.
- **Widget** — A fully custom UI fragment or page with its own layout and behavior; may use a dedicated route or a canonical URL with `format=` (see [Widgets](#widgets)).
- **`format` (query parameter)** — Selects either **list density** (`condensed`, `medium`, `large`) on collection **or** singular resource GETs, or an **HTMX / fragment response** (`htmx-search-results`, `htmx-<custom-name>`, etc.). The same value should mean the **same visual density** on list and detail where applicable; see [List and collection URLs](#list-and-collection-urls-and-format).
- **Condensed / medium / large** — Three standard ways to present list data; default is **condensed**.

Related: [STANDARDS.md](STANDARDS.md), [HTMX_PATTERNS.md](HTMX_PATTERNS.md), [OOP_endpoint_useage.md](OOP_endpoint_useage.md), [REQUIREMENTS.md](../REQUIREMENTS.md), [VISION.md](../VISION.md).

---

## Principles

- Use **Bulma** for layout and components, consistent with [STANDARDS.md](STANDARDS.md) and vendored assets under [bulma-1.0.4/](bulma-1.0.4/).
- Add a thin **project CSS** file only for tokens (spacing, brand color), **sharp corners** (see [Visual language](#visual-language-tokens)), and small overrides—avoid forking Bulma unless necessary.
- Prefer a **server-rendered multi-page application (MPA)** that feels like **one coherent product**: standard links and forms, shared layout, and **Django `request.session`** for transient UI state so a **full reload** returns the user to the **same step and data** (especially in [guided flows](#multi-step-flows)). This is not the same as mounting unrelated SPAs; it means predictable server HTML and session-backed continuity. Details: [HTMX_PATTERNS.md](HTMX_PATTERNS.md) §1.

---

## Global chrome

- **Breadcrumbs:** Every page includes a trail back to the **root of the application** (first crumb is the app or product name—e.g. the home/dashboard for that app—not a generic “Home” unless that is the product convention). Error pages (403/404/500) should also include breadcrumbs when feasible so users can recover context.
- **Page title:** Pair breadcrumbs with a clear heading (`h1`) in `main` for the current page.

Breadcrumbs may live in a shared block extended from [templates/base.html](../../templates/base.html) or an include; keep markup consistent across apps.

---

## Visual language (tokens)

- **Sharp corners:** Do not use rounded “pill” styling for boxes, fields, cards, modals, or buttons unless an exception is documented. Implement via the **project CSS** layer by setting Bulma/CSS variables (for example radius variables used by `.box`, `.card`, `.input`, `.textarea`, `.button`, `.modal-card`, `.dropdown`) to `0` so the UI stays consistently square-edged across components.

---

## Layout: cards as the default container

- **Portals and primary forms:** Wrap the main content in a **`.card`**. Put copy and fields in **`.card-content`** (and/or the card body as appropriate). Put **actions in `.card-footer`**—do not float submit buttons outside the card when the page is form-centric.
- **Primary action placement:** The **submit** control sits in the **card footer**, anchored to the **bottom-right half** of the footer row. If **Clear** or **Reset** is present, it occupies the **left quarter**. The remaining quarter is for optional secondary actions (e.g. “Cancel”) or left empty.

**Canonical footer pattern (Bulma `columns`):** use one shared partial or copy this structure so all forms stay aligned.

```html
<footer class="card-footer">
  <div class="columns is-mobile is-vcentered is-gapless">
    <div class="column is-3">
      <!-- Clear / Reset (optional) -->
    </div>
    <div class="column is-3">
      <!-- Secondary action (e.g. Cancel) or leave empty -->
    </div>
    <div class="column is-6 is-flex is-justify-content-flex-end">
      <!-- Primary submit: block or full-width of this column as needed -->
    </div>
  </div>
</footer>
```

Primary submit should remain visually dominant; destructive actions stay de-emphasized and confirm when irreversible.

---

## Tabs

- Use **`<div class="tabs is-boxed">`** for tab navigation.
- Tabs are **left-justified** (default flex start; avoid `is-centered` / `is-right` unless a specific design review approves).
- Skip tabs when there is only one section—use a heading instead.

---

## List and collection URLs (`format`)

Collection URLs follow the **plural resource** pattern in [OOP_endpoint_useage.md](OOP_endpoint_useage.md) (for example `…/events-application/events`). **Singular resource** URLs follow the detail pattern (for example `…/events-application/event/<id>`). Use the same **`template fragments and visual format`** query vocabulary for **both**: list and detail should **look like the same design system at the same density**—for example `…/events?format=medium` and `…/event/<id>?format=medium` share typography, spacing, and information density conventions for that resource type.

| `format` value | Purpose |
| :--- | :--- |
| **`condensed`** (default) | Table: column titles and one row per record; show only fields native to that table when possible. Omit `format` or set `format=condensed`. |
| **`medium`** | Short, full-width rows or boxes—richer than a flat table (joins, summaries), still scannable. |
| **`large`** | Card list: complex relationships and **expected interactivity** (actions, expandable regions, embedded controls). |

**HTMX / fragment `format` values** (same query parameter name, different contract) are defined in [OOP_endpoint_useage.md](OOP_endpoint_useage.md) §3.6 and [HTMX_PATTERNS.md](HTMX_PATTERNS.md)—for example `format=htmx-search-results`, `format=htmx-focused`.

### Custom formats and dedicated fragment paths

- **Custom `format` values** are allowed when a screen needs behavior or markup that does not fit the standard densities or shared HTMX names. Use predictable names, for example **`format=htmx-<special-name>`** on the **canonical** singular or collection URL (for example `…/event/<id>?format=htmx-event-timeline`). Document the name in the view or app docs so clients and tests stay aligned.
- **Dedicated fragment routes** are an **exception** when branching on `format=` (or combined query rules) makes the view unmaintainable—heavy portal-specific logic, many partials, or clear ownership boundaries. In that case you may expose a sub-path such as **`…/event/<id>/fragments/<portalname>`** (replace `portalname` with a stable identifier). Prefer **`format=` on the canonical URL** first ([OOP_endpoint_useage.md](OOP_endpoint_useage.md) §3.6); add a fragment path only when the tradeoff is justified and the route does not duplicate a second “CRUD” API for the same resource without reason.

### Mutual exclusion and defaults

- The server accepts **at most one** `format` value per request for these conventions.
- **Do not combine** list-density values (`condensed`, `medium`, `large`) with **HTMX fragment** values (`htmx-*`) in the same URL. If a client sends conflicting values, the view should **reject** the request (for example 400) or apply a documented **precedence rule**—prefer validation over silent merge.
- **Default:** For collection GET requests with no `format`, render **`condensed`**. For **singular** GET requests with no `format`, use the **same default density** as the list for that resource type (**`condensed`**) so navigation between list and detail does not change visual scale unless the user chose a different `format`.

| | Full page (typical) | Fragment-only (HTMX) |
| :--- | :--- | :--- |
| **List density** | `condensed` / `medium` / `large` | Not used—use `hx-select` on a full page when possible ([HTMX_PATTERNS.md](HTMX_PATTERNS.md) §6). |
| **HTMX** | N/A | `htmx-search-results`, `htmx-focused`, etc. |

Pagination and sorting remain query parameters alongside `format`; see [REQUIREMENTS.md](../REQUIREMENTS.md) NFR-PERF-001.

---

## Widgets

Some key data types may expose **widgets**: fully custom markup and behavior.

- **Dedicated routes** are allowed for bespoke experiences, for example:
  - `…/events-application/event/<event-id>/get-widget`
  - `…/events-application/events-widget-list`
- When a widget is “just another view” of an existing resource, prefer the **canonical URL + `format=`** pattern from [OOP_endpoint_useage.md](OOP_endpoint_useage.md) §3.6 so the same addressable resource does not sprawl across duplicate paths. If a widget grows too complex for query parameters alone, see [Custom formats and dedicated fragment paths](#custom-formats-and-dedicated-fragment-paths).
- See [HTMX_PATTERNS.md](HTMX_PATTERNS.md) §7 for focused widgets and fragment rules.

---

## Multi-step flows

**Portals vs steps:** A **portal** (see glossary) is a whole area of the app (events, restocking, etc.). Inside one portal, a **guided flow** is implemented as **one create (or edit) page**, not a chain of different pages for each step.

- Prefer **one route** (for example `…/events/create`) with **vertical scroll** and **all steps on the same document**.
- **Later steps** are **shown** (headings, cards, or sections) but **disabled** (non-interactive fields, `disabled` / `aria-disabled`, or server-side omission of POST handlers) until prior steps pass validation.
- **Final submission** is available only when every step is complete.
- Persist step and draft field state in **session** (namespaced), aligned with [HTMX_PATTERNS.md](HTMX_PATTERNS.md) §2.C.

**Do not** model “step 1 of 3” as three separate URLs for the same draft resource unless there is an exceptional reason (bookmarking deep steps, very heavy server work per step); the default pattern is visibility + progressive enablement on **one** page.

---

## HTMX and progressive enhancement

- **Baseline:** Implement flows with **full page loads** and **session-backed state** first. Confirm behavior with standard form POST and redirects.
- **Layer HTMX** after the baseline works, following [HTMX_PATTERNS.md](HTMX_PATTERNS.md) (for example `hx-select` on full pages, fragment exceptions where documented).
- **Exceptions** where HTMX is expected even during initial design:
  - **Search** bars that return result fragments (`format=htmx-search-results`, …).
  - **Fields with more than eight options** where a typeahead, searchable dropdown, or lazy-loaded select improves usability—use HTMX as in [HTMX_PATTERNS.md](HTMX_PATTERNS.md) §3.

---

## Forms

- Labels associated with inputs; show validation errors next to fields and a summary if needed.
- Field order follows natural reading order (top to bottom, left to right). The **canonical primary submit** for the form lives in the **card footer** per [Layout: cards](#layout-cards-as-the-default-container); avoid duplicating a second primary submit in the card body.

---

## Modals

- Prefer the **native `<dialog>` element** (`showModal()` / `close()`, focus management, backdrop) rather than ad-hoc div overlays.
- **Structure:** wrap Bulma’s **`.modal-card`** (head, body, foot) **inside** the `<dialog>`. Use the project reset class on the dialog root so native dialog chrome aligns with Bulma (see below).
- Close actions should call **`dialog.close()`** (for example via `this.closest('dialog').close()` on buttons) and use an explicit **Close** control with `aria-label="close"` where it is icon-only.

```html
<dialog id="my-dialog" class="php-modal-reset">
  <div class="modal-card">
    <header class="modal-card-head">
      <p class="modal-card-title">Modal Title</p>
      <button class="delete" aria-label="close" onclick="this.closest('dialog').close()"></button>
    </header>
    <section class="modal-card-body">
      <p>Native dialog functionality with Bulma styling!</p>
    </section>
    <footer class="modal-card-foot">
      <button class="button is-success">Save changes</button>
      <button class="button" onclick="this.closest('dialog').close()">Cancel</button>
    </footer>
  </div>
</dialog>
```

---



## Tables and data density

- Paginate long lists ([REQUIREMENTS.md](../REQUIREMENTS.md) NFR-PERF-001).
- Sticky header optional for wide tables inside `table-container`.
- Choose **condensed / medium / large** per [List and collection URLs](#list-and-collection-urls-and-format).

---

## Accessibility (baseline)

- **Keyboard:** All interactive elements focusable; logical tab order.
- **Semantic HTML:** `main`, `nav`, headings in order.
- **Color contrast:** Meet WCAG AA where feasible for text and controls (NFR-A11Y-001 in [REQUIREMENTS.md](../REQUIREMENTS.md)).
- **Fonts:** Inside form inputs, prefer **monospace** faces with clear distinction among `0`, `O`, `I`, `1`, `l`.
- **RTL:** Footer “right half” and left-aligned tabs assume **LTR**; mirror layout if RTL is introduced later.

---

## Empty, loading, error states

- **Empty:** Explain why there is no data and the next step (e.g. “No assets yet—create one”).
- **Loading:** HTMX `htmx-request` class on indicators; avoid layout shift where possible.
- **Error:** Human-readable message; 403/404/500 pages distinct in production.

---

## Common mistakes

- **Duplicate routes** for list density or HTMX variants—use **one collection URL** and branch on `format` ([OOP_endpoint_useage.md](OOP_endpoint_useage.md) §3.6); same idea for singular URLs before adding `…/fragments/…`.
- **List and detail with the same `format`** but **unrelated styling**—breaks the shared-density rule; align templates or tokens for that resource.
- **Mixing** list-density `format` values with **`htmx-*`** in one query string—invalid; validate explicitly.
- **Inconsistent card footers**—copy-paste diverges; use one **footer partial** with the canonical column layout.
- **Multi-step wizards** split across many URLs when a **single-scroll** pattern was intended—inconsistent back/forward and session handling.
- **Adding HTMX before** plain POST/redirect works—harder to debug and weakens the accessibility baseline.
- **Long lists** without pagination—violates NFR-PERF-001.

---

## Related documents

- [HTMX_PATTERNS.md](HTMX_PATTERNS.md) — Dynamic behavior, session drafts, search exception, CSRF.
- [OOP_endpoint_useage.md](OOP_endpoint_useage.md) — Routes, collections, `format` for partials.
- [VISION.md](../VISION.md) — User goals.
