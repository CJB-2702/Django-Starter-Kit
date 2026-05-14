# UI Decisions — Structural Examples

This document captures the design decisions made while building the kitchen-sink structural examples (`work-portal-example`, `search-page-example`, `index-example`). These examples define reusable page patterns and navigation conventions for the EBAMS application.

---

## Overview

Three distinct page structures were designed to cover the common patterns in the application:

1. **Work Portal** — Detail view of a work item (event, task, asset) with actions and metadata
2. **Search Page** — Searchable list/table with filters, results, and bulk operations
3. **Index / Portal Hub** — Role-based or feature-area entrypoint with portals/options

All three share a common chrome (top nav, portals dropdown, sidebars) but differ in content layout, navigation, and visual hierarchy.

---

## Navigation Architecture

### Top Navigation Bar
- **Fixed height:** 3rem
- **Components:** EBAMS brand, portal tabs (Events, Administration, Assets, Maintenance, Inventory, Core), global search, user menu
- **Portal tabs:** Clicking opens a second bar (portal dropdown) with context-specific links for that portal

### Portal Dropdown
- **Trigger:** Click a portal tab
- **Behavior:** Opens below the topnav, showing a list of sub-links for the selected portal (e.g., "Maintenance" → "Work Orders", "Scheduled", "Procedures", etc.)
- **Toggle:** Clicking the active tab again closes the dropdown

### Main Left Sidebar (Collapsible)
- **Default state:** Expanded on search and index pages; collapsed on work portals
- **Content:** Section-scoped navigation links (e.g., "Roles & Access", "Users", "Data Ownership" for administration)
- **Style:** Light background, grouped by section with dividers, active link highlighted with left border and primary color
- **Collapse mechanism:** Hamburger (☰) in topnav toggles `.is-sidebar-collapsed` class on the shell; grid shrinks from 220px to 0 width
- **Visual feedback:** Hamburger shows `.is-active` highlight when sidebar is collapsed

### In-Page Navigation Sidebar (Work Portals Only)
- **Default:** Visible and prominent on work portal pages
- **Content:** Jump links to sections within the current page (e.g., "Event Details", "Event Activity", "Actions", "Procedure Notes")
- **Style:** Light background, slightly narrower (180px) than main sidebar, active link highlighted with left border
- **Behavior:** 
  - Clicking a link smoothly scrolls the main content area to that section
  - As the user scrolls, the active link indicator follows the currently visible section
- **Purpose:** Helps users navigate long or complex detail pages without excessive scrolling

---

## Page Structure & Layout

### Container & Grid
- **Max-width:** 1200px, centered with auto margins
- **Grid columns (dynamic):**
  - Default (search, index): `220px [main nav] | 1fr [content]`
  - Work portal: `220px [main nav] | 180px [in-page nav] | 1fr [content]`
  - When sidebar collapsed: `0 | [in-page nav] | 1fr` or `0 | 1fr`

### Page Hero (Work Portals)
- **Purpose:** Prominently display page title, primary actions, and quick stats at a glance
- **Structure:** Single card-like container with:
  - Page title + icon + subtitle on the left
  - Primary action buttons on the right (larger than default, not `is-small`)
  - Stat bar (4-column grid) below the title row
- **Styling:**
  - Light background card
  - Left accent border (3px, primary color)
  - Buttons inside are bumped up in size (0.95rem font, 0.55em padding) to feel prominent
  - Page title scaled to 1.85rem

### Stat Cards (Quick Info Row)
- **Structure:** 4-column grid of info cards (Status, Priority, Actions, Blockers)
- **Each card:** Color-coded accent bar on top (left edge), label in gray, value in strong text
- **Use:** At the top of work portals to surface the most critical info without scrolling
- **Accent colors:** Gray, blue, green, red — can be customized per stat type

### Body Grid Layout
- **Work portal:** `.body-grid.has-rail` = `3fr [main content] | 1fr [quick actions rail]`
  - Main content scrolls with the right rail (both inside the scrollable area)
  - Right rail contains Quick Actions (buttons), Assignment, Summary stats, Related links
  - Allows users to see context (rail) while reading main content without repositioning

- **Search page:** `.body-grid.full-width` = `1fr [entire content]`
  - Filters card (full width)
  - Results table (full width)
  - No right rail

- **Index/hub:** `1fr [centered content]`
  - Centered hero title + subtitle
  - Primary action card (full width, call-to-action style)
  - Role cards (3 across)
  - Summary stats (4 across)

---

## Scrolling & Fixed Elements

- **Top nav:** Fixed to viewport, always visible, z-index 40
- **Portal dropdown:** Fixed below topnav, z-index 30
- **Main sidebar:** Independent scroll within its own column (can scroll its content, but column position is fixed)
- **In-page nav sidebar:** Independent scroll within its own column
- **Main content area (scrollarea):** `overflow-y: auto`, contains the max-width container and all body content
  - Right rail (on work portals) is *inside* the scrollarea, so it scrolls together with main content
  - This means users don't lose context (the rail) while reading long sections

---

## Work Portal Pattern

**When to use:** Viewing a single record (maintenance event, work order, asset, part demand) with associated metadata, actions, assignments, and related items.

**Key features:**
- Hero wrapper for title + primary actions + quick stats
- In-page nav for section jumping (prominent and sticky)
- 3/4 + 1/4 split: main details on left, auxiliary info (quick actions, assignment, summary) on right
- Scrollable right rail so context stays visible without pinning
- Section IDs and scroll-margin for smooth anchor navigation

**Examples:**
- Brake Inspection Procedure (maintenance event)
- Asset detail view
- Part demand detail view

---

## Search / List Page Pattern

**When to use:** Browsing and filtering a list of records with bulk operations and drill-down into details.

**Key features:**
- Full-width filters card with multi-column search inputs (allows complex filtering)
- Full-width results table with pagination
- No right rail (all space for content)
- Collapsible main sidebar (on by default)
- Stat bars for quick counts

**Examples:**
- Part Demands
- Asset list
- Work Order queue

---

## Index / Portal Hub Pattern

**When to use:** A portal's home page offering multiple role-based or feature-based entry points.

**Key features:**
- Centered hero with icon + title + subtitle (psychological focal point)
- Primary CTA card (large, prominent) for the most common action
- Role/feature cards in a grid (3 across typical)
- Summary stats bar at the bottom showing key metrics
- No right rail, no in-page nav (simple, focused)

**Examples:**
- Maintenance Portal home
- Administration portal home
- Events portal home

---

## Color & Styling Decisions

- **Borders:** 1px solid var(--bulma-border-weak); left accents on cards are thicker (3px) and use primary color for emphasis
- **Radius:** 0 (no rounding, sharp corners throughout for a modern utilitarian feel)
- **Button sizes:** 
  - Default in cards: no size modifier (Bulma default ~2.5em)
  - In hero: larger for prominence (0.95rem font, manual padding)
  - In rail: `is-small` for compactness
  - In list actions: mixed, varies per use case
- **Active states:** Left border + primary color text + light background on nav links; `.is-active` class
- **Typography:**
  - Section labels: 0.6–0.65rem, uppercase, letter-spaced, gray text
  - Page titles: 1.85rem in hero; 1.25rem in standard headers
  - Body: Bulma default 0.875rem

---

## Technical Notes

### Base Template Structure
- [`_base.html`](app/public_app/templates/kitchen_sink/structural_examples/_base.html) — Shared chrome and layout
  - Defines topnav, portal dropdown, shell grid, sidebars, scrollarea, container
  - Provides blocks: `sidebar`, `inpage_nav`, `content`, `shell_class`, `active_portal`, `active_sublink`
  - Includes JS for portal dropdown rendering and in-page nav scroll tracking

### Page Extensions
- [`work_portal.html`](app/public_app/templates/kitchen_sink/structural_examples/work_portal.html) — Sets `shell_class = has-inpage-nav is-sidebar-collapsed`, uses hero, right rail
- [`search_page.html`](app/public_app/templates/kitchen_sink/structural_examples/search_page.html) — Full-width filters and results, no sidebar collapse by default
- [`portal_index.html`](app/public_app/templates/kitchen_sink/structural_examples/portal_index.html) — Centered hero with role cards

### In-Page Navigation (Work Portals)
- Links are anchors (`#sec-details`, etc.)
- Clicking a link programmatically scrolls `.app-scrollarea` (not the window)
- As user scrolls main content, JS tracks which section is at the top and updates active link state
- Sections have `scroll-margin-top: 1rem` so anchors land below chrome

### Sidebar Collapse
- Controlled by `.is-sidebar-collapsed` class on `.app-shell`
- Toggle function `toggleSidebar()` is exposed in JS
- Hamburger button calls this and syncs its visual `.is-active` state
- Grid transitions smoothly (0.18s ease)

---

## Future Enhancements

1. **Responsive breakpoints:** Current design assumes desktop. Add mobile breakpoints where sidebars collapse at narrow widths.
2. **Persistence:** Store collapse state in localStorage so it survives navigation (currently resets per page based on default).
3. **Right rail pinning (optional):** On very long work portals, consider making the right rail `position: sticky` at the bottom so it stays visible even if content is very long.
4. **Breadcrumbs:** Add breadcrumb nav at the top of search/detail pages to indicate location in hierarchy.
5. **Keyboard shortcuts:** Alt+/ to open portal dropdown, Esc to close, arrow keys to navigate.
6. **Search page pagination:** Current paginator is static; wire it to actually paginate results.

---

## Kitchen Sink Links

- [Work Portal Example](http://localhost:8000/kitchen-sink/work-portal-example)
- [Search Page Example](http://localhost:8000/kitchen-sink/search-page-example)
- [Index / Portal Hub Example](http://localhost:8000/kitchen-sink/index-example)

All three pages are referenced from the [Kitchen Sink index](http://localhost:8000/kitchen-sink/) under "Page Examples".
