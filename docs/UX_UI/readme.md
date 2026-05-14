# UX / UI

The goal of this folder is to provide comprehensive components and rules for developing the front end of Bulma + HTMX applications. The conventions here apply to **every** server-rendered page in the project.

## Index

| Document | Purpose |
| :--- | :--- |
| [UX_UI.md](UX_UI.md) | Visual language, layout, `format=` density contract, modals, accessibility baseline. The top-level reference. |
| [form_style_guide.md](form_style_guide.md) | Action layout rules — Create / Edit / Delete / Cancel geometry on cards, forms, and inline addons. |
| [component_library/searchbars.md](component_library/searchbars.md) | `<search-dropdown>` web component (picker) and plain HTMX search inputs (filter). |
| [component_library/dual_listbox_guide.md](component_library/dual_listbox_guide.md) | Dual listbox pattern for editing many-to-many relationships. |
| [component_library/common_buttons.md](component_library/common_buttons.md) | Standard button table — icons, semantic colors, Bulma classes per action. |

## How these docs relate

- **[UX_UI.md](UX_UI.md)** is the top-level reference: visual tokens, the `format=` contract, modals, multi-step flows.
- **[form_style_guide.md](form_style_guide.md)** specializes the "actions" part of UX_UI.md into a reusable geometry.
- **`component_library/`** holds reusable, named components. Each file is the single source of truth for that component — its when-to-use, its markup, its server contract, and its mistakes.

When in doubt, the resolution order is: `component_library/<specific-component>.md` → [form_style_guide.md](form_style_guide.md) → [UX_UI.md](UX_UI.md).

## Related architecture docs

- [docs/ARCHITECTURE/HTMX_PATTERNS.md](../ARCHITECTURE/HTMX_PATTERNS.md) — HTMX conventions, CSRF, session drafts.
- [docs/ARCHITECTURE/ENDPOINT_PATTERNS.md](../ARCHITECTURE/ENDPOINT_PATTERNS.md) — OOP endpoints and the `format=` query contract.
- [docs/ARCHITECTURE/STANDARDS.md](../ARCHITECTURE/STANDARDS.md) — engineering principles.
- [docs/ARCHITECTURE/COMMON_UI_COMPONENTS.md](../ARCHITECTURE/COMMON_UI_COMPONENTS.md) — pagination, shared partials.
