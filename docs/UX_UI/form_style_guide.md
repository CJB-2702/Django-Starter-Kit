# Form & Action Layout Style Guide

How **Create**, **Edit**, **Delete**, **Cancel**, and other actions are positioned on cards, forms, and inline controls. The geometry is the same everywhere in the app so users build muscle memory: *primary on the bottom-right, dangerous things small and far from the primary*.

Related: [UX_UI.md](UX_UI.md) (Layout: cards as the default container), [common_buttons.md](component_library/common_buttons.md), [HTMX_PATTERNS.md](../ARCHITECTURE/HTMX_PATTERNS.md).

---

## Core rule

> **All Create/Edit/Delete/Cancel actions live at the bottom of their parent container.**

The "parent container" is whichever of these is closest:
1. A `.card` (preferred) → actions go in `.card-footer`.
2. A `<form>` directly inside `.card-content` → actions go in a footer row at the bottom of the form.
3. An inline form-addon (single field) → submit is flush against the field; see [Special case](#special-case-inline-single-field-forms).

Never float buttons outside the card. Never anchor buttons to the viewport.

---

## Geometry

Inside the footer row:

| Slot | Width | Contents |
| :--- | :--- | :--- |
| **Bottom-right (primary)** | **50%** of the footer row | The single primary action (Save / Create / Submit / Apply). Full-width within its 50% column. |
| **Bottom-left (secondary)** | Remaining 50%, **inline** | Cancel, Reset, and (where applicable) Delete. Smaller buttons, left-aligned, inline with each other. |

```
+----------------------------------------------------------+
|                                                          |
|  card-content (fields, copy)                             |
|                                                          |
+----------------------------------------------------------+
| [Cancel] [Reset] [Delete]      |       [   Save   ]      |
+----------------------------------------------------------+
       <-- secondary 50% -->         <-- primary 50% -->
```

### Why 50/50

- Half the row reserves visual weight for the primary action so it is the obvious target.
- The other half packs as many secondary actions inline as you need without the primary moving.
- It is the same geometry on a 320px phone and a 1920px desktop — the columns shrink proportionally.

### Canonical markup

All card footers use a **two-column grid layout** (50/50 split) with inline secondary buttons on the left and a full-width primary button on the right.

The project provides three CSS classes to keep markup clean:

| Class | Applied to | Effect |
| :--- | :--- | :--- |
| `custom-card-footer` | `<footer class="card-footer">` | Grid layout with `grid-template-columns: 1fr 1fr`, `gap: 0.5rem`, and `align-items: stretch` |
| `card-footer-secondaries` | A `<div>` wrapping secondary buttons | Groups Cancel / Reset / Delete on the left with flex layout and `0.5rem` gap. Stretches to full height. Use an **empty div** if there are no secondary buttons. |
| `card-footer-primary` | The primary button | Stretches to full height of the footer. Never add `is-small` to the primary button. |

```html
<footer class="card-footer custom-card-footer">
  <div class="card-footer-secondaries">
    <a href="…" class="button is-small is-light">Cancel</a>
    <button type="reset" class="button is-small is-light">Reset</button>
    <button type="submit"
            class="button is-small is-danger is-light"
            formaction="{% url 'role_delete' role.id %}"
            onclick="return confirm('Delete this role?');">
      Delete
    </button>
  </div>
  <button type="submit" class="button is-primary card-footer-primary">Save</button>
</footer>
```

**Primary-only footer** — keep the empty secondaries container for the left column:

```html
<footer class="card-footer custom-card-footer">
  <div class="card-footer-secondaries"></div>
  <button type="submit" class="button is-primary card-footer-primary">Save</button>
</footer>
```

**Read-only card with Delete (secondary) and Edit (primary)**:

```html
<footer class="card-footer custom-card-footer">
  <div class="card-footer-secondaries">
    <form method="post" action="{% url 'event_soft_delete' hash=event_hash %}" style="margin: 0;">
      {% csrf_token %}
      <button class="button is-small is-danger is-light" type="submit"
        onclick="return confirm('Delete this event?');">
        <span class="icon"><span class="material-icons" aria-hidden="true">delete</span></span>
        <span>Delete</span>
      </button>
    </form>
  </div>
  <a href="{% url 'event_edit' hash=event_hash %}" class="button is-small is-info is-light card-footer-primary">
    <span class="icon"><span class="material-icons" aria-hidden="true">edit</span></span>
    <span>Edit</span>
  </a>
</footer>
```

**Read-only card with only Edit (primary)**:

```html
<footer class="card-footer custom-card-footer">
  <div class="card-footer-secondaries"></div>
  <a href="{% url 'event_edit' hash=event_hash %}" class="button is-small is-info is-light card-footer-primary">
    <span class="icon"><span class="material-icons" aria-hidden="true">edit</span></span>
    <span>Edit</span>
  </a>
</footer>
```

---

## Delete protocol

Delete is always a **secondary** action — it never sits in the primary slot, and it is **visually narrower** than the other secondaries.

| Property | Value |
| :--- | :--- |
| Slot | Bottom-left, inline with Cancel/Reset |
| Style | `is-small is-danger is-light` (light red, not solid red) |
| Width | Capped via `style="max-width: 6rem;"` or `is-small` only — explicitly **less wide** than Cancel |
| Confirmation | Required. Use a native `<dialog>` modal ([modals_dialogs_usage.md](component_library/modals_dialogs_usage.md)) for non-trivial deletes; a `confirm()` is acceptable for low-stakes removals (e.g. a single tag) |
| Position relative to Cancel | **Right of Cancel/Reset** so the user's pointer travels through the safer buttons first |

Never make Delete the primary action of an edit form. If a screen exists *only* to delete a thing (e.g. a "Delete account" confirmation page), the primary action on that screen is the deletion — but that is a dedicated screen, not the edit form.

### Why Delete is small

The button's visual weight should match the **frequency** of the action, not its consequence. Edit and Save happen all day; deletes are rare. A small button keeps it discoverable but not inviting.

---

## Special case: inline single-field forms

When a form has **exactly one** field (renaming a domain, editing a tag label, changing a display name in place), the canonical 50/50 footer is overkill. Use Bulma's **`field has-addons`** pattern instead — submit is flush with the input on its right.

```
+----------------------------------------+----------+
| domain.name                            |  [Save]  |
+----------------------------------------+----------+
```

```html
<form method="post" action="{% url 'domain_rename' domain.id %}"
      hx-post="{% url 'domain_rename' domain.id %}"
      hx-target="#domain-name-block"
      hx-swap="outerHTML">
  {% csrf_token %}
  <div class="field has-addons">
    <div class="control is-expanded">
      <input class="input is-family-monospace"
             type="text" name="name"
             value="{{ domain.name }}"
             required>
    </div>
    <div class="control">
      <button type="submit" class="button is-primary">Save</button>
    </div>
  </div>
</form>
```

Rules for inline forms:

- **No Cancel button.** The user cancels by navigating away or pressing Escape. If the value matters enough to confirm, it does not belong in an inline form.
- **No Delete in an inline form.** Delete affects the row/parent, not the field — put Delete on the parent's footer.
- **Use `is-expanded`** on the input's control so the field grows and the button stays its natural width.
- **Submit on Enter** must work — that is the entire reason this pattern exists. Do not `event.preventDefault()` Enter on the field unless you are also submitting the form.

### When to graduate from inline to a full form

Switch to the full card-footer pattern as soon as the form gains any of:
- A second field
- A required confirmation step
- A Cancel that does anything more than "navigate away"
- Multiple submit actions (e.g. Save vs Save and continue)

Do not bolt extra buttons onto the addons row — it gets crowded fast.

---

## Reset, Clear, and other tertiary controls

Tertiary controls (Reset, Clear all, Restore defaults) live **left of Cancel** in the secondary slot, sized `is-small is-light`. They never appear without a Cancel — if there is nothing to cancel back to, there is nothing to reset to either.

If the form has a **Clear** that empties draft state in `request.session`, prefer wiring it as a regular form submit with `name="action" value="clear"` rather than client-side JS — keeps the F5 rule intact ([UX_UI.md](UX_UI.md)).

---

## Common mistakes

- **Delete in the primary slot.** It is destructive *and* rare — never the dominant action.
- **Solid `is-danger` Delete.** The light variant signals "secondary destructive" and matches Cancel's visual weight.
- **Cancel on the right of Save.** Breaks left-to-right reading: secondary should always be reached *before* primary.
- **Stretching Delete to match Cancel.** Delete must be visibly the **narrowest** button on the row.
- **Adding a duplicate primary submit inside `.card-content`.** The primary lives in the footer; one form, one primary submit.
- **Inline form with a Cancel button.** If you need Cancel, you have outgrown the inline pattern.
- **Per-field "Save" buttons inside a multi-field form.** One submit at the bottom commits the whole form. Use HTMX OOB swaps if you need granular feedback.
