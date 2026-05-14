# Search Bars

Two distinct search patterns live in this app, and they are **not interchangeable**:

1. **`<search-dropdown>`** — a form-associated custom element that pairs an input with an HTMX-loaded dropdown of `<li>` results. **Use this when the search produces a single picked value** that becomes a form field (e.g. picking a permission, a user, an asset).
2. **Plain HTMX search input** — a vanilla `<input>` with `hx-get` that swaps a results region. **Use this when the search drives a list view** (e.g. filtering a table of assets, the *Available* column of a [dual listbox](dual_listbox_guide.md)).

If you find yourself reaching for a third pattern, check the table below before inventing one.

Related: [UX_UI.md](../UX_UI.md), [HTMX_PATTERNS.md](../../ARCHITECTURE/HTMX_PATTERNS.md), [ENDPOINT_PATTERNS.md](../../ARCHITECTURE/ENDPOINT_PATTERNS.md), [dual_listbox_guide.md](dual_listbox_guide.md), [common_buttons.md](common_buttons.md).

---

## Decision table

| Situation | Pattern |
| :--- | :--- |
| Pick **one** related record to attach to a form field (FK, single tag, owner) | `<search-dropdown>` |
| Pick **one of many** for an inline edit (replace a row's owner without leaving the row) | `<search-dropdown>` |
| Filter a **list view** (assets table, events feed) | Plain HTMX input → `?format=htmx-search-results` |
| Filter the *Available* column of a **dual listbox** | Plain HTMX input scoped to that column ([dual_listbox_guide.md](dual_listbox_guide.md)) |
| Type-ahead with **>8 options** for a `<select>` field | `<search-dropdown>` (per [UX_UI.md](../UX_UI.md) — HTMX exception for >8 options) |
| Global "search the whole app" bar in the header | Plain HTMX input, results target a portal-level container |

---

## 1. `<search-dropdown>` — picking a single value

A reusable, **form-associated** custom element that pairs an input with a dropdown of `<li>` results. Backed by an open shadow root; results are projected into a default `<slot>`. Lives at [`app/static/web_components/search_dropdown.js`](../../../app/static/web_components/search_dropdown.js).

### Why a custom element

- **Form participation** via `ElementInternals.setFormValue()` — the picked value submits with the surrounding `<form>` exactly like a native input. No hidden input plumbing.
- **HTMX attribute pass-through** — `hx-get`, `hx-target`, `hx-trigger`, etc. on the host element are forwarded to the internal `<input>`, so the consumer writes plain HTMX without learning new attributes.
- **Shadow-DOM-correct `hx-target`** — defaults to `global #<host-id>` so swaps hit the host element in the document, not a stale node inside the shadow tree (HTMX's bare `#id` resolves against the trigger's root, which is the shadow root here and would miss the host).
- **No JS bindings on consumer pages** — register the script once, drop the tag, done.

### Usage

Register the script once on any page that needs the component (load it in your portal-level template):

```html
<script defer src="{% static 'web_components/search_dropdown.js' %}"></script>
```

Then instantiate. Two examples:

#### A. Permission picker for a role form

```html
<search-dropdown
    id="permission-picker"
    name="permission_id"
    placeholder="search permissions..."
    hx-get="{% url 'permissions_portal_index' %}?format=htmx-search-results&group_id={{ group.id }}"
    hx-trigger="keyup changed delay:300ms, search">
  {# server-rendered <li> results swap into here via HTMX #}
</search-dropdown>
```

The corresponding view returns **only `<li>` elements** (no `<ul>` wrapper), each with `data-value` set to the value that should populate the form on click:

```html
{# templates/access_management/_permission_search_items.html #}
{% for permission in results %}
  <li data-value="{{ permission.id }}" class="is-family-monospace">
    {{ permission.codename }}
    <span class="has-text-grey is-size-7"> — {{ permission.name }}</span>
  </li>
{% empty %}
  <li class="is-disabled">No matches.</li>
{% endfor %}
```

When the user clicks an `<li>`, the component:
1. Reads `data-value` and stores it as the form value (visible to the surrounding `<form>` POST).
2. Sets the visible input text to the `<li>`'s text content.
3. Closes the dropdown.

#### B. Inline owner change on a single row

```html
<form method="post" action="{% url 'asset_set_owner' asset.id %}"
      hx-post="{% url 'asset_set_owner' asset.id %}"
      hx-target="#asset-row-{{ asset.id }}"
      hx-swap="outerHTML">
  {% csrf_token %}
  <search-dropdown
      name="owner_id"
      placeholder="change owner..."
      hx-get="{% url 'users_search' %}?format=htmx-search-results"
      hx-trigger="keyup changed delay:300ms, search">
  </search-dropdown>
</form>
```

The form submits on the user's chosen value with no extra input wiring.

### Server contract — what the endpoint must return

Per [HTMX_PATTERNS.md](../../ARCHITECTURE/HTMX_PATTERNS.md) §3 and [ENDPOINT_PATTERNS.md](../../ARCHITECTURE/ENDPOINT_PATTERNS.md) §3.6:

- **URL:** the canonical collection URL for the resource (e.g. `…/permissions`, `…/users`).
- **Query:** `format=htmx-search-results`, `q=<typed text>`, plus any scope params (`group_id=…`, `org_id=…`).
- **Response body:** **only `<li>` elements** — no surrounding `<ul>`, `<div>`, or template wrapper. The component swaps innerHTML into its slot.
- **Each `<li>`** that should be selectable has a `data-value="<id>"`. Disabled / informational rows omit `data-value` (or set `aria-disabled="true"` / class `is-disabled`).
- **Pagination:** include a sentinel `<li>` (e.g. *"Showing 25 of 412 — refine your search…"*) when the result is truncated. The component does not paginate; it is for type-and-narrow.

### The web component (full source)

```js
/**
 * Bulma-styled search field with a dropdown of <li> results (light DOM / slot).
 * HTMX loads fragments into the host element; use format=htmx-search-results on the collection URL.
 */
class SearchDropdown extends HTMLElement {
  static formAssociated = true;

  constructor() {
    super();
    this.internals = this.attachInternals();
    this.attachShadow({ mode: "open" });
    this._value = "";

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          position: relative;
          width: 100%;
          font-family: BlinkMacSystemFont, -apple-system, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", Helvetica, Arial, sans-serif;
        }
        input {
          width: 100%;
          box-sizing: border-box;
          align-items: center;
          border: 1px solid #dbdbdb;
          border-radius: 4px;
          box-shadow: inset 0 0.0625em 0.125em rgba(10, 10, 10, 0.05);
          display: inline-flex;
          font-size: 1rem;
          height: 2.5em;
          justify-content: flex-start;
          line-height: 1.5;
          padding: calc(0.5em - 1px) calc(0.75em - 1px);
          background-color: #fff;
          color: #363636;
        }
        input:hover { border-color: #b5b5b5; }
        input:focus {
          border-color: #485fc7;
          box-shadow: 0 0 0 0.125em rgba(72, 95, 199, 0.25);
          outline: none;
        }
        input::placeholder { color: rgba(54, 54, 54, 0.3); }
        .dropdown {
          position: absolute;
          left: 0;
          right: 0;
          top: calc(100% + 2px);
          z-index: 20;
          display: none;
          list-style: none;
          margin: 0;
          padding: 0.5rem 0;
          background-color: #fff;
          border-radius: 4px;
          box-shadow: 0 0.5em 1em -0.125em rgba(10, 10, 10, 0.1), 0 0 0 1px rgba(10, 10, 10, 0.02);
          max-height: 16rem;
          overflow-y: auto;
        }
        :host([open]) .dropdown { display: block; }
        ::slotted(li) {
          padding: 0.5rem 0.75rem;
          cursor: pointer;
          font-size: 0.875rem;
          line-height: 1.4;
          color: #363636;
        }
        ::slotted(li):hover,
        ::slotted(li):focus {
          background-color: #f5f5f5;
        }
        ::slotted(li.is-disabled),
        ::slotted(li[aria-disabled="true"]) {
          cursor: default;
          color: #7a7a7a;
        }
        ::slotted(li.is-family-monospace) {
          font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
          font-size: 0.8125rem;
        }
      </style>
      <input type="text" autocomplete="off" placeholder="Search...">
      <ul class="dropdown" role="listbox">
        <slot></slot>
      </ul>
    `;
  }

  connectedCallback() {
    this.input = this.shadowRoot.querySelector("input");

    const passThrough = [
      "hx-get", "hx-post", "hx-trigger", "hx-target", "hx-swap",
      "hx-indicator", "hx-headers", "hx-vals", "hx-params",
      "hx-include", "hx-sync",
    ];
    passThrough.forEach((attr) => {
      if (this.hasAttribute(attr)) {
        this.input.setAttribute(attr, this.getAttribute(attr));
      }
    });

    if (this.hasAttribute("placeholder")) {
      this.input.setAttribute("placeholder", this.getAttribute("placeholder"));
    }

    if (!this.input.hasAttribute("hx-trigger")) {
      this.input.setAttribute("hx-trigger", "keyup changed delay:350ms, search");
    }

    if (!this.input.hasAttribute("hx-target")) {
      if (!this.id) {
        this.id = `search-dropdown-${Math.random().toString(36).slice(2, 11)}`;
      }
      // HTMX resolves bare #id from the trigger's root (shadow root here), so the host id is invisible.
      // "global " forces document-scoped querySelector (htmx hx-target extended syntax).
      this.input.setAttribute("hx-target", `global #${this.id}`);
    }

    if (!this.input.hasAttribute("hx-swap")) {
      this.input.setAttribute("hx-swap", "innerHTML");
    }

    this.input.setAttribute("name", "q");

    if (window.htmx) {
      htmx.process(this.input);
    }

    this.addEventListener("click", (e) => {
      const li = e.target.closest("li");
      if (!li || !this.contains(li)) return;
      if (!li.hasAttribute("data-value")) return;
      const raw = li.getAttribute("data-value");
      if (raw === null || raw === "") return;
      this.value = raw;
      this.input.value = li.innerText.trim();
      this.removeAttribute("open");
    });

    this.input.addEventListener("focus", () => this.setAttribute("open", ""));
    this.input.addEventListener("blur", () => {
      setTimeout(() => this.removeAttribute("open"), 200);
    });
  }

  get value() { return this._value; }

  set value(v) {
    this._value = v;
    this.setAttribute("value", v);
    this.internals.setFormValue(v);
  }

  get name() { return this.getAttribute("name"); }
}

if (!customElements.get("search-dropdown")) {
  customElements.define("search-dropdown", SearchDropdown);
}
```

### Rules

- **Do not nest** a `<search-dropdown>` inside another `<search-dropdown>`.
- **One per form field.** If a form needs to pick *two* related records, ship two separate `<search-dropdown>` elements with distinct `name=` attributes.
- **Do not** reach into the shadow DOM from page CSS. Style hooks are: `::slotted(li)`, `::slotted(li.is-disabled)`, `::slotted(li.is-family-monospace)`. If you need a new variant, add the `::slotted` rule to the component, not to a stylesheet.
- **Always set `name=`** on the host element if the picked value should submit with the form. The component proxies `name` to `setFormValue`, but it cannot guess.
- **The `q` parameter is fixed.** The component sets `name="q"` on the internal input — your endpoint must read `q`, not `query` or `term`.
- **Keep the `<li>` markup flat.** Nested `<details>` or interactive children inside `<li>` will steal click events from the component's selection handler.

### Common pitfalls

- **Empty results show no feedback.** Always render an "No matches" `<li class="is-disabled">` so the dropdown is not silently empty.
- **`hx-target` set to a stale element.** Don't override `hx-target` unless you know the shadow-DOM caveat above. The default works for 99% of cases.
- **Picking does not update the form.** You forgot `data-value` on the `<li>`, or you forgot `name=` on the host.
- **Results are wrapped in a `<ul>` or `<div>`.** Strip them — the component already provides the `<ul>`. Wrapping breaks the slot projection styling.

---

## 2. Plain HTMX search input — filtering a list

For list-filtering use cases, do **not** use `<search-dropdown>`. A plain Bulma input plus `hx-get` to the canonical list URL with `format=htmx-search-results` is the right tool.

### Pattern

```html
<div class="field">
  <p class="control has-icons-left">
    <input class="input is-family-monospace"
           type="search" name="q"
           hx-get="{% url 'asset_list' %}?format=htmx-search-results"
           hx-trigger="keyup changed delay:350ms, search"
           hx-target="#asset-list-container"
           hx-swap="innerHTML"
           hx-push-url="true"
           hx-indicator=".asset-list-skeleton"
           placeholder="search assets...">
    <span class="icon is-small is-left">
      <i class="fa-solid fa-magnifying-glass"></i>
    </span>
  </p>
</div>

<div id="asset-list-container">
  {% include "assets/_asset_list_rows.html" %}
</div>
```

The view returns the list rows fragment (a `<table>` body, a series of `.box` rows, etc.) — whatever the canonical list URL returns at the requested density.

### Rules

- **`type="search"`** so the browser provides a clear-X button and the `search` event fires on clear.
- **`hx-push-url="true"`** so the back button works after a search — keeps the F5 rule honest.
- **Same canonical URL** as the unfiltered list, with `?q=…&format=htmx-search-results`. Do not invent a `/search` route.
- **Debounce ~350ms.** Less feels twitchy on a slow DB; more feels broken.
- **Indicator class** so the user sees the request is in flight; pair with a Bulma skeleton block.

---

## Common mistakes (across both patterns)

- **Using `<search-dropdown>` to filter a list.** It is a *picker*, not a *filter*. Use the plain HTMX input.
- **Using a plain HTMX input as a picker** when you need a single value to submit with a form. You will end up reinventing form participation badly. Use `<search-dropdown>`.
- **Two `format=` values in one URL** (e.g. `format=htmx-search-results&format=large`). The server should reject this — see [UX_UI.md](../UX_UI.md) on `format=` mutual exclusion.
- **Server returns a fully-rendered page** to a search request. Search responses are fragments. Use `format=htmx-search-results` and return only what the target needs.
- **No `hx-push-url`** on a list filter — back button is broken, bookmarks don't work.
