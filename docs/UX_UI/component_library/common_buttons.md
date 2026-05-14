# Common Buttons & Iconography

The complete table of standard action buttons used across the app, paired with their **icon**, **semantic color**, and **Bulma class set**. The point of this doc is uniformity: a "Save" button looks the same on every page, in every form, in every modal.

Related: [form_style_guide.md](../form_style_guide.md), [UX_UI.md](../UX_UI.md), [searchbars.md](searchbars.md), [dual_listbox_guide.md](dual_listbox_guide.md).

We use **Material Icons** (vendored in `app.css`, loaded from `static/fonts/material-icons/`). Icons are **never decorative-only on a button** — every icon has the action's text label beside it, except in the [icon-only](#icon-only-buttons) cases listed below.

```html
<span class="icon"><span class="material-icons" aria-hidden="true">icon_name</span></span>
```

---

## Master button table

| Action | Material Icon name | Color | Bulma classes | When to use |
| :--- | :--- | :--- | :--- | :--- |
| **Save** | `save` | Primary (blue) | `button is-primary card-footer-primary` | Commit form changes to the database. Primary slot, bottom-right. |
| **Create** | `add` | Primary (blue) | `button is-primary card-footer-primary` | Create a new resource. On a list page, top-right; on a create form, primary slot. |
| **Apply** | `check` | Primary (blue) | `button is-primary card-footer-primary` | Apply staged/filter changes (e.g. apply a search filter, apply a permission diff). |
| **Submit** | `send` | Primary (blue) | `button is-primary card-footer-primary` | Submit a request to a workflow (e.g. submit an event for approval). |
| **Edit** | `edit` | Info (cyan) | `button is-info is-light is-small card-footer-primary` | Navigate to the edit form for a resource. Primary slot on read-only cards. |
| **Cancel** | `close` | Light grey | `button is-small is-light` | Discard unsaved changes and return to the previous view. Secondary slot. |
| **Reset** | `restart_alt` | Light grey | `button is-small is-light` | Restore the form to its initial values without leaving the page. Secondary slot. |
| **Delete** | `delete` | Danger light (pink) | `button is-small is-danger is-light` | Remove a resource. Always small, always confirmed. See [form_style_guide.md](../form_style_guide.md#delete-protocol). |
| **Remove** | `remove` | Danger light (pink) | `button is-small is-danger is-light` | Detach an item from a relation (e.g. remove a permission from a role). |
| **Refresh** | `refresh` | Link (blue) | `button is-link is-light` | Re-fetch the current view's data without a full page reload. Pairs with HTMX `hx-get`. |
| **Search** | `search` | n/a (icon-only) | inside `<search-dropdown>` | See [searchbars.md](searchbars.md). |
| **Filter** | `filter_list` | Light grey | `button is-light` | Open a filter panel or apply filter chips. |
| **Sort** | `sort` | Light grey | `button is-light` | Open the sort selector. |
| **Export** | `file_download` | Link (blue) | `button is-link is-light` | Download data (CSV, JSON). Always opens a download, never replaces the current view. |
| **Import** | `file_upload` | Link (blue) | `button is-link is-light` | Upload data. Opens a modal or a dedicated page. |
| **Approve** | `check_circle` | Success (green) | `button is-success` | Affirmative state transition (approve, publish, activate). Solid — it commits state. |
| **Reject** | `cancel` | Warning (yellow) | `button is-warning is-light` | Negative state transition that is **not destructive** (reject, deactivate, archive). |
| **Restore** | `restore` | Success light (green) | `button is-small is-success is-light` | Undo a soft delete or revert to a prior version. |
| **Copy** | `content_copy` | Light grey | `button is-small is-light` | Copy a value to the clipboard (IDs, slugs, codenames). Icon-only is acceptable. |
| **Settings** | `settings` | Light grey | `button is-light` | Open settings for the current resource. |
| **More / Menu** | `more_vert` | Light grey | `button is-small is-light` | Open a dropdown of less-frequent actions. Icon-only. |
| **Close** | `close` (or `delete` Bulma element) | n/a | `delete` (Bulma) inside `<dialog>` headers | Dismiss a modal or banner. Icon-only. |

---

## Semantic colors — what each color *means*

| Color | Bulma class | Meaning |
| :--- | :--- | :--- |
| **Primary** (blue) | `is-primary` | The expected, intended action. There is **at most one** primary button per form/card. |
| **Info** (cyan) | `is-info` | Navigation that is read-mostly (Edit, View, Open). Uses `is-light` variant by default. |
| **Link** (royal blue) | `is-link` | Side-effect-free actions (Refresh, Export, Import preview). |
| **Success** (green) | `is-success` | Affirmative state transitions (Approve, Activate, Restore). |
| **Warning** (yellow) | `is-warning` | Cautionary actions that are reversible (Reject, Archive, Deactivate). |
| **Danger** (red/pink) | `is-danger` | Destructive actions (Delete, Remove). **Always paired with `is-light`** in inline footers; use solid `is-danger` only on dedicated confirmation pages. |
| **Light grey** | `is-light` (no color modifier) | Neutral / secondary (Cancel, Reset, Filter, Sort). |

The **light variant** (`is-light` in addition to a color class) softens the button so it does not compete with a true primary. Most non-primary buttons in this app use `is-light`.

---

## Sizes

| Size | Class | When to use |
| :--- | :--- | :--- |
| Default | *(none)* | Primary actions, top-of-page navigation, form submits |
| Small | `is-small` | Secondary actions in card footers (Cancel, Reset, Delete) |
| Normal | *(none)* | Default — covers most cases |
| Medium | `is-medium` | Hero CTAs (rare; only on the dashboard or empty-state cards) |
| Large | `is-large` | Reserved for empty-state primary CTAs ("Create your first asset") |

A footer row should never mix default-size and `is-small` *primary* buttons — pick one tier and stick to it.

---

## Icon-only buttons

Icon-only is acceptable for these actions **only**:

- **Close** (modal/banner dismiss) — `aria-label="close"` required.
- **Copy** (copy ID/slug to clipboard) — `aria-label="copy <value>"`.
- **More / Menu** (overflow dropdown) — `aria-label="more actions"`.
- **Search** trigger inside `<search-dropdown>` — handled by the component.
- **Sort direction toggle** in a column header.
- **Any button inside a `<table>` row** — see [Buttons in tables](#buttons-in-tables).

Anywhere else, an icon must travel with a text label. A bare `<i class="fa-solid fa-trash">` is not a delete button — it is an accessibility incident.

---

## Buttons in tables

> **Rule:** Buttons that live inside a `<table>` row are rendered as **icon-only**. The action's text label moves to the `title` attribute (native hover tooltip) and `aria-label` (screen-reader equivalent).

### Why

Table rows are visually dense. Repeating "Edit / Delete / Restore" on every row creates noise and stretches the actions column out of proportion to the data columns. The icon set is consistent enough across the app that the symbol alone is recognisable; the tooltip is there for first-time users and the `aria-label` keeps it accessible.

This is the **only** place in the app where Edit, Delete, Approve, Reject, Restore — actions that **always** travel with a text label elsewhere — drop their label.

### Markup

Wrap actions in `.buttons.are-small` so spacing and sizing stay consistent within the row, and right-align with `is-justify-content-flex-end`:

```html
<td class="has-text-right">
  <div class="buttons are-small is-justify-content-flex-end">
    <a class="button is-info is-light is-small"
       title="Edit {{ row.name }}"
       aria-label="Edit {{ row.name }}"
       href="{% url 'asset_edit' row.id %}">
      <span class="icon"><span class="material-icons" aria-hidden="true">edit</span></span>
    </a>
    <button type="submit"
            class="button is-danger is-light is-small"
            title="Delete {{ row.name }}"
            aria-label="Delete {{ row.name }}"
            onclick="return confirm('Delete {{ row.name }}?');">
      <span class="icon"><span class="material-icons" aria-hidden="true">delete</span></span>
    </button>
  </div>
</td>
```

### Rules

- **Always include both `title` and `aria-label`.** `title` shows on hover; `aria-label` is what screen-readers read out. They should contain the same text and **identify the specific row** ("Delete asset-beta", not just "Delete").
- **Always include the row identifier in the label** so screen-reader users hear which row's button has focus. "Delete" is ambiguous — "Delete asset-beta" is not.
- **Sizes:** Always `is-small`. The default-sized button is too tall for table-row density.
- **Color semantics are unchanged.** Edit stays `is-info is-light`, Delete stays `is-danger is-light`, Approve stays `is-success`, etc. Only the text label disappears.
- **Header column:** Title the actions column "Actions" (or leave blank if obvious). Right-align with `has-text-right`.
- **Max 4 actions per row.** If you have more, collapse the rare ones behind a `more_vert` overflow button.

### When NOT to apply this rule

Outside tables, icon + text remains the default. The rule is **inside `<table>` rows only** — not inside a `.card` listing rows-as-boxes, not inside `.media`, not inside a `<dl>`. Density is the trigger, and the table is what makes that density acute.

---

## Markup snippets

Icons use **Material Icons** (vendored in `app.css`): `<span class="icon"><span class="material-icons" aria-hidden="true">icon_name</span></span>`.

### Save (primary — in `.card-footer` right slot)

```html
<button type="submit" class="button is-primary card-footer-primary">
  <span class="icon"><span class="material-icons" aria-hidden="true">save</span></span>
  <span>Save</span>
</button>
```

### Cancel (secondary, small, light)

```html
<a href="{% url 'role_detail' role.id %}" class="button is-small is-light">
  <span class="icon"><span class="material-icons" aria-hidden="true">close</span></span>
  <span>Cancel</span>
</a>
```

### Delete (small, danger-light, narrower than Cancel)

```html
<button type="submit"
        class="button is-small is-danger is-light"
        formaction="{% url 'role_delete' role.id %}"
        onclick="return confirm('Delete this role?');"
        style="max-width: 6rem;">
  <span class="icon"><span class="material-icons" aria-hidden="true">delete</span></span>
  <span>Delete</span>
</button>
```

### Edit (navigation, info-light — primary slot on read-only cards)

```html
<a href="{% url 'role_edit' role.id %}"
   class="button is-info is-light is-small card-footer-primary">
  <span class="icon"><span class="material-icons" aria-hidden="true">edit</span></span>
  <span>Edit</span>
</a>
```

### Refresh (HTMX, no full reload)

```html
<button type="button" class="button is-link is-light is-small"
        hx-get="{% url 'asset_list' %}?format=condensed"
        hx-target="#asset-list-container"
        hx-swap="innerHTML"
        hx-indicator=".asset-list-skeleton">
  <span class="icon"><span class="material-icons" aria-hidden="true">refresh</span></span>
  <span>Refresh</span>
</button>
```

---

## Common mistakes

- **Multiple primary buttons** on the same card. Pick one. Anything else is `is-info`/`is-link`/`is-light`.
- **Solid `is-danger`** Delete in a card footer. Use `is-danger is-light` — solid red is reserved for dedicated confirmation pages.
- **Icon without label** outside the [icon-only](#icon-only-buttons) list. Add `<span>Label</span>` next to the icon.
- **Different icons for the same action** across pages (e.g. `delete` on one page, `cancel` on another for Delete). Stick to this table.
- **Color drift:** using `is-warning` for Delete because "yellow looks less aggressive". Delete is `is-danger is-light`. Always.
- **Custom CSS to recolor a button.** If you need a new semantic, add it to this table first; do not invent one-off colors per page.
