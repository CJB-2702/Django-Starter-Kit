# Modals & Dialogs

Modal and dialog components in this project use the native HTML `<dialog>` element styled with Bulma cards. The `commandfor` and `command` attributes provide a declarative way to trigger and control dialogs without JavaScript event listeners.

## Overview

- **`<dialog>`** — native HTML element for modal behavior (backdrop, focus trap, Escape to close)
- **Bulma `.card`** — provides the visual card styling and structure
- **`commandfor` & `command`** — custom attributes for declarative control of dialog state

## Basic Structure

```html
<!-- Trigger button -->
<button class="button is-primary" commandfor="demo-dialog" command="show-modal">
  Open Dialog
</button>

<!-- Dialog element -->
<dialog id="demo-dialog" class="card" style="padding: 0;">
  <header class="card-header">
    <p class="card-header-title">Dialog Title</p>
    <button class="delete is-large" aria-label="close" 
            commandfor="demo-dialog" command="close"></button>
  </header>

  <div class="card-content">
    <div class="content">
      <!-- Dialog content here -->
    </div>
  </div>

  <footer class="card-footer custom-card-footer">
    <div class="card-footer-secondaries">
      <button type="submit" class="button is-small is-light" 
              commandfor="demo-dialog" command="close">Cancel</button>
      <button type="reset" class="button is-small is-light">Reset</button>
      <button type="submit" class="button is-small is-danger is-light" 
              onclick="return confirm('Delete this item?');">Delete</button>
    </div>
    <button type="submit" class="button is-primary card-footer-primary" 
            commandfor="demo-dialog" command="close">Save</button>
  </footer>
</dialog>
```

## commandfor & command Attributes

### `commandfor`
Points to the `id` of the target `<dialog>` element.

### `command`
The action to perform on the dialog:
- **`show-modal`** — open the dialog (`dialog.showModal()`)
- **`close`** — close the dialog (`dialog.close()`)

### Example Usage

```html
<!-- Open dialog -->
<button commandfor="my-dialog" command="show-modal">Open</button>

<!-- Close dialog (close button in header) -->
<button commandfor="my-dialog" command="close" class="delete"></button>

<!-- Close dialog (Cancel button in footer) -->
<button commandfor="my-dialog" command="close" class="button">Cancel</button>
```

## Dialog Anatomy

### Header
- `.card-header` — contains the title and close button
- `.card-header-title` — the dialog title
- `.delete` — the close button (top-right corner)

### Content
- `.card-content` — the main body of the dialog
- `.content` — wraps the actual content (paragraph text, forms, etc.)

### Footer
- `.card-footer.custom-card-footer` — action buttons footer with grid layout
- `.card-footer-secondaries` — wraps secondary buttons (Cancel, Reset, Delete)
- `.card-footer-primary` — the primary action button (Save)

## CSS Classes

### `custom-card-footer`
Grid layout for the footer with two columns:
- Left: secondary buttons (Cancel, Reset, Delete)
- Right: primary button (Save)

All buttons stretch to full height.

```css
.custom-card-footer {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.5rem;
  padding: 0;
  align-items: stretch;
}
```

### `card-footer-secondaries`
Flex container for secondary buttons with full height stretch.

```css
.card-footer-secondaries {
  display: flex;
  align-items: stretch;
  gap: 0.5rem;
  padding: 0;
  height: 100%;
}
```

### `card-footer-primary`
Primary button that stretches to full height.

```css
.card-footer-primary {
  height: 100%;
}
```

## Button Sizes & Styles

Use standard Bulma button classes:
- **Secondary buttons:** `class="button is-small is-light"`
- **Danger buttons:** `class="button is-small is-danger is-light"`
- **Primary button:** `class="button is-primary card-footer-primary"`

## Dialog Styling

Set `style="padding: 0;"` on the dialog element to remove default padding and let the card handle all spacing.

## Complete Example

See [app/static/test_dialog.html](../../../app/static/test_dialog.html) for a working demo.

## Browser Support

The native `<dialog>` element is supported in all modern browsers. The `commandfor` and `command` attributes are custom and require JavaScript implementation via a framework or custom script.

## Accessibility

- Close button has `aria-label="close"` for screen readers
- `<dialog>` provides built-in focus management and backdrop
- Escape key closes the dialog automatically
- Modal behavior traps focus within the dialog
