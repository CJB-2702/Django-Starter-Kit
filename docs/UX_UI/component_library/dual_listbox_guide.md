# Dual Listbox Component Guide

A **dual listbox** presents two side-by-side lists — *Available* and *Selected* — with controls to move items between them. It is a deliberate, high-friction control: every move is explicit and visible. We use it when a multi-select must be **auditable**, **bulk-editable**, and **comprehensible at a glance**.

Related: [UX_UI.md](../UX_UI.md), [HTMX_PATTERNS.md](../../ARCHITECTURE/HTMX_PATTERNS.md), [ENDPOINT_PATTERNS.md](../../ARCHITECTURE/ENDPOINT_PATTERNS.md), [searchbars.md](searchbars.md).

---

## When to use

Pick **dual listbox** over a standard `<select multiple>` or tag-style multi-select when **all** of these hold:

| Condition | Why it matters |
| :--- | :--- |
| Editing a **many-to-many** relationship (e.g. `User.permissions`, `Asset.tags`, `Role.permission_groups`) | Both sides of the relation should be visible at once. |
| The set of *selected* items can grow into the dozens | A flat tag chip strip becomes unscannable past ~10 entries. |
| The user needs to **review what is currently selected** before submitting | Selected list acts as a confirmation surface. |
| The **available** pool benefits from search / filter | The component pairs naturally with a search bar over the *Available* side. |
| The change is **irreversible-ish** (saved on submit, not on click) | A dual listbox stages changes; nothing commits until POST. |

Pick a **standard multi-select** (or a single search dropdown) when:

- The expected selection is **0–3 items** (use a single `<search-dropdown>` instead — see [searchbars.md](searchbars.md)).
- The relation is **conceptually one-to-many on the form** (use a single select or radio group).
- Selection is **immediate / autosaved** (use a chip add-remove pattern instead — the dual listbox's "stage then submit" model is wasted).
- The available pool is **fixed and small** (under ~8 options) — use checkboxes.

If you are tempted to ship two dual listboxes on the same page, step back: that is usually a sign the page should be split into two edit screens, or the relation should be inverted.

---

## Anatomy

```
+------------------------------+    +------------------------------+
| Available                    |    | Selected (12)                |
| +--------------------------+ |    | +--------------------------+ |
| | search...                | |    | | search selected...       | |
| +--------------------------+ |    | +--------------------------+ |
| +--------------------------+ |    | +--------------------------+ |
| | [ ] asset.read           | |    | | [ ] user.create          | |
| | [ ] asset.write          | |    | | [ ] user.delete          | |
| | [ ] asset.delete         | |    | | [ ] role.assign          | |
| | [ ] event.read           | |    | | ...                      | |
| | ...                      | |    | |                          | |
| +--------------------------+ |    | +--------------------------+ |
+------------------------------+    +------------------------------+
                  [ Save ]   [ Cancel ]
```

- **Two equal columns** in a Bulma `.columns` row, each a `.box` or `.card`.
- Each column has a **title with a count** (e.g. *Selected (12)*) — the count is always visible.
- Each column has its **own search bar** scoped to that column's contents.
- Movement controls live **between** columns: a vertically stacked pair of arrow buttons, OR clickable rows on each side. Prefer **clickable rows** with a chevron icon — fewer mouse trips.
- The form's **primary submit lives in the parent card footer**, not inside either listbox column. See [form_style_guide.md](../form_style_guide.md).

---

## Implementation (Django + HTMX)

We do **not** ship a dedicated `<dual-listbox>` web component. The pattern is two HTMX-driven server-rendered lists that stage changes in `request.session`, and a single POST commits the diff.

### Template skeleton

```html
{# templates/permissions/_dual_listbox_role_permissions.html #}
<div class="columns" id="role-permissions-dual">
  <div class="column is-half">
    <div class="card">
      <header class="card-header">
        <p class="card-header-title">Available permissions</p>
      </header>
      <div class="card-content">
        <input class="input is-family-monospace"
               type="text" name="q_available"
               hx-get="{% url 'role_permissions_dual' role.id %}?format=htmx-available"
               hx-trigger="keyup changed delay:300ms"
               hx-target="#available-list"
               hx-swap="innerHTML"
               placeholder="search permissions...">
        <ul id="available-list" class="dual-listbox-list">
          {% include "permissions/_dual_listbox_available_items.html" %}
        </ul>
      </div>
    </div>
  </div>

  <div class="column is-half">
    <div class="card">
      <header class="card-header">
        <p class="card-header-title">
          Selected permissions ({{ selected_count }})
        </p>
      </header>
      <div class="card-content">
        <input class="input is-family-monospace"
               type="text" name="q_selected"
               hx-get="{% url 'role_permissions_dual' role.id %}?format=htmx-selected"
               hx-trigger="keyup changed delay:300ms"
               hx-target="#selected-list"
               hx-swap="innerHTML"
               placeholder="search selected...">
        <ul id="selected-list" class="dual-listbox-list">
          {% include "permissions/_dual_listbox_selected_items.html" %}
        </ul>
      </div>
    </div>
  </div>
</div>
```

### Item partial (a single row)

```html
{# templates/permissions/_dual_listbox_available_items.html #}
{% for permission in available_permissions %}
  <li>
    <button type="button"
            class="button is-fullwidth is-justify-content-flex-start is-family-monospace"
            hx-post="{% url 'role_permissions_dual' role.id %}"
            hx-vals='{"action": "add", "permission_id": {{ permission.id }}}'
            hx-target="#role-permissions-dual"
            hx-swap="outerHTML">
      <span class="icon"><i class="fa-solid fa-chevron-right"></i></span>
      <span>{{ permission.codename }}</span>
    </button>
  </li>
{% empty %}
  <li class="has-text-grey">No matches.</li>
{% endfor %}
```

The *selected* partial is symmetrical: `action: "remove"` and a left-facing chevron.

### View / endpoint

Follow the canonical-URL + `format=` contract from [ENDPOINT_PATTERNS.md](../../ARCHITECTURE/ENDPOINT_PATTERNS.md):

| Method | URL | `format=` | Purpose |
| :--- | :--- | :--- | :--- |
| GET  | `/admin/roles/<id>/permissions-dual` | *(none)* | Full page render of both lists |
| GET  | `/admin/roles/<id>/permissions-dual` | `htmx-available` | `<li>` rows for the *Available* list (filtered by `q_available`) |
| GET  | `/admin/roles/<id>/permissions-dual` | `htmx-selected`  | `<li>` rows for the *Selected* list (filtered by `q_selected`) |
| POST | `/admin/roles/<id>/permissions-dual` | *(none)* | Stage one move (`action=add\|remove`, `permission_id=...`); returns the **whole `#role-permissions-dual` block** so counts update |
| POST | `/admin/roles/<id>/permissions` | *(none)* | **Commit** the staged set to the DB; redirect 303 to the role page |

Staged state lives in `request.session['role_<id>_permissions_draft']` (a list of permission IDs). The session is the source of truth for the dual listbox until the user clicks **Save** on the parent form, at which point the role's permissions are replaced with the staged list inside one transaction.

### Why POST per move (not pure client-side staging)

- The **F5 rule** ([UX_UI.md](../UX_UI.md)): a full-page reload must restore the staged state. Session is the simplest place to keep it.
- Each move re-renders the **whole pair** (`#role-permissions-dual`), so the counts in both headers stay correct without manual JS bookkeeping.
- It keeps the diff visible to the user: refresh the page, the staged-but-uncommitted state survives until they hit Save or Cancel.

### Cancel behavior

A **Cancel** button on the parent form should:
1. POST to a `cancel` action that pops `request.session['role_<id>_permissions_draft']`.
2. Redirect to the role detail page (303).

Do not rely on the user closing the tab — orphaned drafts are a debugging nuisance.

---

## API design (REST-shaped)

For non-HTMX consumers (admin tools, scripted bulk edits) the same resource exposes a JSON contract under the same URL:

```
GET    /admin/roles/<id>/permissions
       -> 200 { "selected": [12, 34, 56], "available_count": 412 }

GET    /admin/roles/<id>/permissions?available=true&q=asset
       -> 200 { "items": [{"id": 12, "codename": "asset.read"}, ...], "page": 1, "next": 2 }

PUT    /admin/roles/<id>/permissions
       Body: { "selected": [12, 34, 99] }
       -> 204  (replaces the entire set; idempotent)

PATCH  /admin/roles/<id>/permissions
       Body: { "add": [99], "remove": [56] }
       -> 200 { "selected": [12, 34, 99] }
```

`PUT` for a full replace, `PATCH` for incremental ops — same contract whether the client is the dual listbox UI or a script. The HTMX endpoints are **not** a parallel API; they share the same view and dispatch on `format=` per [ENDPOINT_PATTERNS.md](../../ARCHITECTURE/ENDPOINT_PATTERNS.md).

---

## Accessibility

- Each list is a `<ul>` with `role="listbox"` and `aria-multiselectable="true"`.
- Each row's button uses the permission codename as its accessible name; do not bury it in a tooltip.
- The two column headers (*Available* / *Selected (12)*) are real `<h2>` / `<h3>` elements so screen readers announce structure.
- Keyboard: `Tab` enters the *Available* search, `Tab` again moves to the first row; `Enter` moves a row to the other side; the same focused index keeps focus after the swap so a user can move multiple in sequence.

---

## Common mistakes

- **One column doing all the work.** If *Selected* is just a comma-joined chip strip under the *Available* list, that is a tag input, not a dual listbox.
- **Auto-saving on every move.** Defeats the "review before commit" property; if you want autosave use a chip pattern instead.
- **No count in the header.** Users cannot tell at a glance whether a change took effect.
- **Search bar that searches both sides.** Each column owns its own search state; otherwise filtering one hides relevant rows in the other.
- **Putting Save inside one of the two columns.** Submit lives in the parent card footer, not inside the listbox.
