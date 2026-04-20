## `search-dropdown` (HTMX + Bulma-styled)

Reusable **form-associated** custom element: `app/static/web_components/search_dropdown.js`. Register the script on pages that need it (see `permission_group_portal.html`).

- **Results contract:** Point `hx-get` at the canonical collection URL with **`format=htmx-search-results`** and **`q`** (and optional **`page`**, **`group_id`**, etc.). The response must be **only** `<li>` elements (no wrapper), swapped into the host via `innerHTML` so they project into the default slot. See `HTMX_PATTERNS.md` §3 and `ENDPOINT_PATTERNS.md` §3.6.
- **Example (administration):** `{% url 'permissions_portal_index' %}?format=htmx-search-results&group_id=<id>` — partial template `access_management/_permission_search_items.html`.
- **HTMX + shadow DOM:** The trigger input lives in an open shadow root, so a bare `hx-target="#…"` is resolved against that shadow tree and misses the host. The component defaults to **`hx-target="global #&lt;id&gt;"`** (HTMX extended syntax) so swaps hit the `<search-dropdown>` element in the document.

---

PAGINATION EXAMPLE

<nav class="pagination is-centered" role="navigation" aria-label="pagination">
  <a href="#" class="pagination-previous">Previous</a>
  <a href="#" class="pagination-next">Next page</a>
  <ul class="pagination-list">
    <li><a href="#" class="pagination-link" aria-label="Goto page 1">1</a></li>
    <li><span class="pagination-ellipsis">&hellip;</span></li>
    <li><a href="#" class="pagination-link" aria-label="Goto page 45">45</a></li>
    <li>
      <a
        class="pagination-link is-current"
        aria-label="Page 46"
        aria-current="page"
        >46</a
      >
    </li>
    <li><a href="#" class="pagination-link" aria-label="Goto page 47">47</a></li>
    <li><span class="pagination-ellipsis">&hellip;</span></li>
    <li><a href="#" class="pagination-link" aria-label="Goto page 86">86</a></li>
  </ul>
</nav>

