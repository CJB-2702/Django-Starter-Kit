# EBAMS HTMX & Progressive Enhancement Guidelines

## Core Philosophy: "Enhanced, Not Defined"
The application must remain a functional Django Multi-Page Application (MPA) at its core. HTMX is used to layer interactivity and "snappiness" on top of standard browser behaviors. 

**Note:** These are loose guidelines intended to keep the codebase maintainable and the user experience consistent. They are not firm rules; specific widgets or complex interfaces may require exceptions at the developer's discretion.

---

### 1. The Baseline: Static-First Development
* **The F5 Rule:** Every page and state should be reachable and functional via a standard static page reload.
* **Session-Driven State:** Use the Django `request.session` dict to track transient UI states, wizard progress, or "just updated" flags. This ensures that if a user refreshes the page, the server knows exactly what to render.
* **Django Source of Truth:** Prefer getting the **full page** back from the server. Use HTMX to pluck the relevant components out of that full response.

### 2. General Interaction Patterns

#### A. Editing Existing Models
When updating a model (e.g., changing an event description) within a portal:
1.  **POST** the data to the standard Django update endpoint.
2.  The server processes the change and redirects (303) to the detail or parent page.
3.  HTMX fetches the full target page but uses `hx-select` to isolate the specific component.
4.  **Feedback:** Include a Django "Success" message in the response. Use an Out-of-Band (OOB) swap or a client-side trigger to flash this message to the user.

#### B. Adding Data to Existing Items
When adding a child entity (e.g., adding a comment to an event):
1.  Perform a `POST` to the creation endpoint.
2.  The server should re-render or redirect to the **entire parent entity** (the Event Card).
3.  HTMX replaces the entire parent container.
    * *Why:* This ensures that side effects—like updated comment counts or "last activity" timestamps—are updated automatically without managing multiple partials.

#### C. The Creation Workflow: Namespaced Session Sub-Components
For adding sub-fields or related data to an item before it is committed to the database (e.g., adding an "Assigned User" while on the `/events/create` page):

1.  **Namespaced Storage:** To avoid "loose data" in the session, always store draft information under a nested dictionary specific to the feature.
    ```python
    # Example: Session Structure
    request.session['event_draft'] = {
        'assigned_users': [1, 5, 12],
        'temp_title': "Project EBAMS Launch"
    }
    ```
2.  **POST via HTMX:** Submit the sub-component data (e.g., User ID) to a specialized "Session-Update" endpoint.
3.  **No Database Commit:** The server validates the data and updates the nested dictionary in `request.session['event_draft']`. Set `request.session.modified = True` to ensure nested changes are saved.
4.  **Full Page Refresh / HX-Get:** The server responds with a redirect or HTMX-triggered fetch of the full `/events/create` page.
5.  **Template Logic:** The Django template reads the session dict to render the "Assigned User" badge or table row as if it were a saved database object.
6.  **Finalization & Cleanup:** When the user hits "Create Event," the view pulls data from the session, performs a bulk commit to the database, and immediately deletes the namespace: `del request.session['event_draft']`.

### 3. The Search Bar Exception (Partial Templates)
While most of the app uses `hx-select` on full pages, **Search Bars are a defined exception.** Search results should always utilize a dedicated partial template for speed and reduced server load.

* **URL / query contract:** Use the **same canonical route** as for the normal list or child collection (no parallel “search-only” path). Add **`format=htmx-search-results`** plus the search query (for example **`q`**). The view branches on **`format`** and returns **only** the results fragment (for example `_results_list.html`) when **`htmx-search-results`** is present—see **`OOP_endpoint_useage.md` §3.6** (one addressable endpoint, query parameters choose full page vs fragment).
* **Example URL:** `.../comments?format=htmx-search-results&q=query`
* **Input Config:**
    ```html
    <input type="text" name="q" 
           hx-get="{% url 'comment-search' %}?format=htmx-search-results" 
           hx-trigger="keyup changed delay:500ms, search" 
           hx-target="#search-results-container" 
           hx-push-url="true"
           hx-indicator=".search-skeleton">
    ```

### 4. Visual Feedback: Bulma Skeletons
To maintain a high-quality feel during server round-trips, use Bulma’s skeleton/loading states.

* **Indicator Targeting:** Use the `.htmx-indicator` class on Bulma skeleton elements.
* **Implementation:** Wrap your components in a container that toggles between the real data and the skeleton during the request.
    ```html
    <div id="event-card-container" class="is-relative">
        <div class="htmx-indicator">
            <div class="skeleton-block" style="width: 100%; height: 200px;"></div>
            <div class="skeleton-lines">
                <div></div><div></div><div></div>
            </div>
        </div>

        <div class="htmx-content-wrapper">
             <button hx-get="/events/1/" 
                     hx-target="#event-card-container" 
                     hx-select="#event-card-content"
                     hx-indicator=".htmx-indicator">
                 Refresh Details
             </button>
             <div id="event-card-content">
                 </div>
        </div>
    </div>
    ```

---

### 5. CSRF, Django middleware, and HTTP methods (GET, POST, PUT, PATCH, DELETE)

HTMX may use **`hx-get`**, **`hx-post`**, **`hx-put`**, **`hx-patch`**, and **`hx-delete`** so the browser sends the same verbs as the OOP endpoint design (`OOP_endpoint_useage.md`). That aligns with REST-style routes while keeping CSRF protection.

**Django middleware:** Ensure **`django.middleware.csrf.CsrfViewMiddleware`** is included in **`MIDDLEWARE`** (this is Django’s default). For views that use it, **unsafe methods**—**`POST`**, **`PUT`**, **`PATCH`**, and **`DELETE`**—require a valid CSRF token; **`GET`** and safe **`HEAD`** do not. The middleware accepts the token from the **`X-CSRFToken`** header on AJAX-style requests, including those issued by HTMX, so the base-template hook below applies to every mutating verb.

**Base template (all pages):** Include the following once in the project base template (for example `templates/base.html`) so every HTMX request sends the CSRF token header:

```html
<script>
    document.body.addEventListener('js/htmx:configRequest', (event) => {
        event.detail.headers['X-CSRFToken'] = '{{ csrf_token }}';
    });
</script>
```

Rely on the **`django.template.context_processors.csrf`** context processor (default with `django.template.backends.django.DjangoTemplates`) so `{{ csrf_token }}` resolves in templates.

**Request bodies and `request.POST`:** For **PUT** and **PATCH**, Django does not populate **`request.POST`** from typical form bodies the way it does for **POST**. Views should read the payload in the way your API defines (for example **`request.body`** with JSON, or **`QueryDict`** parsing where appropriate). This is independent of CSRF: the middleware still enforces CSRF when configured as above.

---

### 6. Technical Implementation Preferences

* **Full documents vs fragment-only responses (aligned with `OOP_endpoint_useage.md` §3.6):** There is **no** conflict between “prefer `hx-select`” and “partials via query parameters.”
    * **Default:** The server renders a **full HTML page** for the resource URL. HTMX uses **`hx-select="#fragment-id"`** to pull a piece of that response into the DOM—**without** a separate route and **without** returning HTML that is only a partial. The URL stays canonical; the “partial” is a slice of the full document.
    * **When a fragment-only response is required** (for example **§3** search results, or **§7** focused widgets): keep the **same canonical URL** and branch on **query parameters** (for example **`format=htmx-search-results`**, **`format=htmx-focused`**, pagination). The view returns **only** the partial template for that request. That matches OOP §3.6: one addressable endpoint, parameters choose full page vs fragment—not a duplicate path for each template variant.
* **Prefer `hx-select` for the default case:** Avoid creating many `_partial.html` files **unless** you are in the fragment-only cases above. For ordinary portals and detail updates, render the full page and use `hx-select="#target-id"` so view and URL logic stay simple.
* **Boosting:** Use `hx-boost="true"` on top-level navigation and main content containers to convert standard links into AJAX requests automatically.
* **CSS Transitions:** Utilize the `htmx-swapping` and `htmx-settling` classes to smooth out the replacement of large components, preventing "content jump."
* **Status Codes:** Ensure the server returns appropriate HTTP status codes (e.g., `422 Unprocessable Entity` for form validation errors) so HTMX can trigger the correct logic. For HTML flows, use the same semantics consistently with the OOP control layer; machine-oriented APIs may document additional codes separately.

---

### 7. Exceptions to the Rule
While full-page refreshes and session-dict state are the standard, **Focused Widgets** (e.g., a real-time search bar, a complex drag-and-drop kanban, or a live notification bell) are outlined as exceptions. These may return **fragment-only** HTML and use specialized HTMX triggers (`hx-trigger="keyup changed delay:500ms"`) to avoid unnecessary overhead. Implement them with the **same canonical URL + `format=` (or related query params)** pattern as in **§6** and **`OOP_endpoint_useage.md` §3.6**, not ad hoc duplicate routes.

For routing, HTTP methods, and query-parameter conventions shared with the control layer, see **`OOP_endpoint_useage.md`** (especially §3.6 for partials on the same route).