# Current UI Problems

Captured during the Kitchen Sink design session — `http://localhost:8000/kitchen-sink/`.

These issues span the project, not just the kitchen sink page. Fixes belong in `app/static/css/app.css` plus targeted template updates.

---

## 1. Icons overlap button text

**Where:** Every icon-paired button on the page — Create, Save, Edit, Delete, Cancel, Reset, etc.

**Symptom:** The Material Icons glyph visibly overlaps the adjacent `<span>` label (e.g. "+ Create" with the plus glyph touching the C; "🗑 Delete" with the trash icon biting into the D).

**Cause:** `app.css` line 43:
```css
.button .icon .material-icons {
  font-size: 1.125em;
  width: 1em;
  height: 1em;
}
```
The font-size is 1.125em but width/height is constrained to 1em, so the rendered glyph is wider than its bounding box and bleeds past the gap that Bulma reserves between `.icon` and the label span.

**Fix:** Drop the `width`/`height` constraint (let the glyph occupy its natural box) or scale them to match the font-size (`width: 1.125em; height: 1.125em;`). Also add a small right margin to `.button .icon:first-child` if Bulma's default gap isn't enough.

---

## 2. Page does not follow system dark-mode preference

**Where:** Everywhere. Reported with OS set to dark mode but the page renders with white card/page backgrounds.

**Cause:** Bulma 1.0 supports `prefers-color-scheme: dark` via its scheme HSL variables, but several places in the project (and the kitchen sink) use **hardcoded light colors**:

- `app.css` does not declare `color-scheme: light dark` on `:root` (so form controls don't darken).
- Kitchen sink uses `background: #fafafa` for `.ks-demo-box`, `#f8f8f8` for `.ks-code`, `has-background-light` on the sidebar, `border: 1px solid #ededed`/`#e8e8e8` — none of these flip in dark mode.

**Fix:**
1. Add `color-scheme: light dark` to `:root` in `app.css`.
2. Replace hardcoded greys in `app.css` and kitchen-sink-local CSS with Bulma scheme variables (`var(--bulma-scheme-main)`, `var(--bulma-scheme-main-bis)`, `var(--bulma-border)`, `var(--bulma-text)`).
3. Make `--bulma-card-radius: 0` so corners stay sharp in either theme.

---

## 3. Card-footer bottom corners are not clipped

**Where:** Card Footer Layouts section — the buttons that line the bottom of a card extend their corners past where the card's corner clipping is expected.

**Cause:** `.custom-card-footer` has `overflow: hidden !important` set, but the **parent `.card`** does not, and Bulma's `--bulma-card-radius` is **not** overridden in `app.css` (only `--bulma-radius`, `--bulma-box-radius`, etc.). So:
- In dark/default-Bulma chrome, the card retains its default rounded corner.
- The button background colors paint through wherever the card's rounded corner is no longer visible.

**Fix:** Override `--bulma-card-radius: 0` in `:root`, and ensure `.card` has `overflow: hidden` so any child element respects the (now-zero) radius regardless of theme.

---

## 4. Inline single-field form: button height ≠ input height

**Where:** Inline Single-Field Form demo (`.field.has-addons`).

**Symptom:** The Save button is visibly shorter than the input next to it.

**Cause:** Project CSS scales `.button` font-size to `calc(var(--bulma-control-size) * 1.25)` while the input keeps the default. Bulma's `.has-addons` aligns by font baseline, not box height, so the mismatched font sizes produce mismatched heights.

**Fix:** In `.has-addons` rows, either drop the button font-scale or pin both controls to the same explicit height. Cleanest is to add to `app.css`:
```css
.field.has-addons .button,
.field.has-addons .input {
  height: var(--bulma-control-height, 2.5em);
}
```

---

## 5. Tabs sit above the card instead of inside it

**Where:** Tabs section.

**Symptom:** `<div class="tabs is-boxed">` is rendered as its own block above the `.card`. Visually it reads as a separate component from the card it controls.

**Fix (per project pattern):** Move tabs **inside** the card, directly under the header (or as the first row of `.card-content`). The tabs and card become one composite component, the active tab governs the content below.

```html
<div class="card">
  <div class="card-content" style="padding-bottom:0;">
    <div class="tabs is-boxed mb-0">
      <ul>…</ul>
    </div>
  </div>
  <div class="card-content">
    … panel content …
  </div>
  <footer class="card-footer custom-card-footer">…</footer>
</div>
```

---

## 6. Empty-state CTA should live in the card footer (full width)

**Where:** Empty States section.

**Current:** Centered button inside `.card-content`.

**Project rule:** Primary actions live in the card footer. For an empty state with one action, that action should occupy the **full footer width** (no secondaries column).

**Fix:** Move the "Create Asset" button into a `card-footer.custom-card-footer` with the secondaries div empty and the primary button stretched full width.

---

## 7. Sidebar: dark-mode text on light-mode background

**Where:** Left navigation rail (`.ks-sidebar.has-background-light`).

**Symptom:** Background remains hardcoded light grey while text picks up the dark-mode color, producing low contrast (faint grey-on-light-grey).

**Cause:** `has-background-light` is a fixed Bulma color, not a theme-aware variable.

**Fix:** Replace with `background: var(--bulma-scheme-main-bis); border-right-color: var(--bulma-border);` so the rail flips with the theme.

---

## 8. NEW RULE — buttons inside table rows must be icon-only with tooltips

**Decision (this session):** Buttons that live inside `<table>` rows must be rendered as **icon-only** controls with the action text supplied via the `title` attribute (and `aria-label` for screen readers). The full text label is reserved for buttons that sit outside table rows.

**Why:** Rows are visually dense. Repeating "Edit", "Delete" once per row clutters the layout and stretches column widths. The icon library is consistent enough across the app that the symbol alone is recognizable, with the tooltip there for first-time users and a11y.

**Where to apply:**
- `app/static/css/app.css` — add `.button.is-table-action` modifier (or just rely on `is-small` + no `<span>` label inside tables).
- `docs/UX_UI/component_library/common_buttons.md` — add a new section "Buttons in tables".
- `templates/.../_list_rows.html` partials project-wide — migrate over time.

**Markup pattern:**
```html
<a class="button is-info is-light is-small"
   title="Edit asset"
   aria-label="Edit asset"
   href="…">
  <span class="icon"><span class="material-icons" aria-hidden="true">edit</span></span>
</a>
```

---

## Fix priority

1. **High — site-wide:** icon overlap (#1), dark-mode support (#2), card-radius/overflow (#3).
2. **Medium — kitchen sink + future migrations:** new table-button rule (#8), tabs-inside-card pattern (#5), empty-state footer rule (#6).
3. **Low — cosmetic:** inline-form heights (#4), sidebar background (#7).
