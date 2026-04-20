2026-04-18 — Added `.cursor/skills/persistent-memory` skill for one-line append-only notes in this file.
2026-04-18 — Bootstrapped `app.core` (division/org/ownership + auditable user-scope links), `app.administration` portal with contexts/policy/seed_dev, login and static settings.
2026-04-18 — Added `app.public_app` with `/` homepage (login + session note), `/about/` and `/site/about/` filler about page; auth URLs default to `/`.
2026-04-18 — Split user assignment models into `app/core/models/user_assignments/`; on login snapshot ownership group ids and Django permission strings into the session via `user_logged_in`.
2026-04-18 — Data ownership UI lists divisions/orgs/ownership groups scoped to the actor’s memberships unless `is_admin_actor`.
2026-04-18 — Added gitignored `docs/users_and_passwords.md` and root `.gitignore` entry for seeded user reference.
2026-04-18 — Documented Django superuser (`admin` / `DJANGO_SUPERUSER_PASSWORD`) in `docs/users_and_passwords.md` for `/admin/`.
2026-04-18 — Installed django-jazzmin; added `jazzmin` before `django.contrib.admin` and `JAZZMIN_SETTINGS` in `app/config/settings.py`.
2026-04-19 — Added `core.models.groupings` (`DivisionOrganisation`, moved `OrganizationOwnershipGroup`), M2M division link via through table; migration `0002_division_organisation_and_groupings`; slug uniqueness is now global per organization.
2026-04-18 — Merged `app.core` into `app.administration` (models, migrations, admin, auth_session); removed `app.core`; kept legacy `core_*` table names; migration `0003_contenttypes_from_core_app_label`.
2026-04-18 — `.cursor/rules/migration-strategy.mdc`: on any schema-affecting model change, delete project numbered `migrations/*.py` (keep `__init__.py`), wipe DB, `makemigrations` + `migrate` + `seed_dev`.
2026-04-18 — Added root `delete_database_rebuild_models.py` (`--seed`) and `.cursor/skills/delete-database-rebuild-models/SKILL.md`; migration rule points to the script.
2026-04-18 — `delete_database_rebuild_models.py`: explicit per-app `app/<name>/migrations` sweep; delete all files except `__init__.py`, drop `__pycache__`.
2026-04-18 — `migration-strategy.mdc`: no legacy-row cleanup in seeds; `seed_dev` dropped `_remove_legacy_demo_rows`.
2026-04-18 — `seed_dev`: 2 divisions, 4 orgs, 8 ownership groups; `super_admin` + legacy demo-* cleanup; scoped `generic_manager` to North; `users_and_passwords.md` aligned.
2026-04-18 — Reworked the administration portal UX toward Django-admin patterns: dashboard app list, sidebar shell, user changelist with filters/pagination/actions, and HTMX-powered ownership/permissions workflows with selected-user carryover.
2026-04-19 — Added user portal detail page at `user-portal/<id>/` (card layout: general info, action permissions with collapsible groups/direct perms, data permissions); user list rows open detail on click (checkboxes unchanged).
2026-04-19 — User portal detail switched from three-column cards to Bulma boxed tabs (General / Action permissions / Data permissions) with tab panels and keyboard nav.
2026-04-19 — User portal detail: `h3.title.is-6` field headers and spacing blocks to separate labels from values (general, action, data tabs).
2026-04-19 — User portal detail: single scrolling page with three full-width stacked cards (tabs removed); kept field headers inside each card.
2026-04-19 — Enabled `LoginRequiredMiddleware`, removed `@login_required` from administration entrypoints, marked `public_app` views with `@login_not_required` and `PublicLogoutView`.
2026-04-19 — Added `.cursor/rules/public-app-routes.mdc` (public pages only in `app/public_app`; otherwise login middleware).
2026-04-19 — Upgraded dependencies to Django 6.0.x (`requirements.txt` `Django>=6.0,<7`); `manage.py check` clean.
2026-04-19 — Added `generic_admin`-only user portal edit at `user-portal/<id>/edit/` (password, dual-listbox groups/permissions/ownership, reusing DjangoPermissionsContext and OwnershipContext); detail page shows Edit link for admins.
2026-04-19 — `is_admin_actor` / `is_grant_actor` treat Django superusers like full admins for portal policy; user portal edit and grant flows allow superusers.
2026-04-19 — User portal detail: list all effective permissions; each Django group is `<details>` with group name as summary and inherited group permission keys listed inside.
2026-04-19 — User portal edit: grey available permissions already granted via groups; `check_direct_permissions_against_group` POST endpoint + JS debounced check on select with warning panel.
2026-04-19 — Replaced fetch/JSON with HTMX + `_direct_perm_group_check.html` fragment; warning renders under Available column; `htmx:configRequest` CSRF from base template.
2026-04-19 — User portal edit Data permissions: divisions and organizations use dropdown + table (remove per row) instead of dual listbox; ownership groups unchanged.
2026-04-19 — UX_UI.md: added Modals section—prefer `<dialog>` with Bulma `.modal-card` inside and project reset class.
2026-04-19 — User portal edit organizations: add/remove org-only vs org+linked ownership groups (2:1 button widths); `OwnershipContext` overlap-safe removal when orgs share groups.
2026-04-19 — Added `app/static/app.css` (square Bulma radii, ~25% larger button type/padding, self-hosted IBM Plex Mono for form fields) and linked it from administration and public base templates plus login.
2026-04-19 — User portal index: removed bulk checkboxes and action dropdown/POST; list is filter + click row to open user only.
2026-04-19 — Data ownership index is browse-only with sectioned links; added division/org/ownership-group portals. Permissions portal replaced by access-management + permission-group portals; `permissions/` redirects to `access-management/`.
2026-04-19 — Vendored Material Icons TTF under `app/static/fonts/material-icons/`, `@font-face` + `.material-icons` in `app.css`; administration/public templates use icon-only on small actions (remove, disable, dual-listbox) and icon+label on default/full-width buttons.
2026-04-19 — Fixed static paths after grouping assets: login template uses `css/bulma.min.css`; `app.css` `@font-face` URLs use `../fonts/...` so fonts resolve from `static/fonts/` when the stylesheet is under `static/css/`.
2026-04-19 — Access management permissions: paginated (32/page) with HTMX + `hx-select` on `#access-permissions-results`; Bulma `pagination` (centered, rounded, elided page numbers via `Paginator.get_elided_page_range`).
2026-04-19 — Added `search-dropdown` web component, `administration_permissions` fragment GET (`format=htmx-search-results`, `group_id`, `q`, `page`), permission-group add-permission form wired to it; documented in `COMMON_UI_COMPONENTS.md`.
2026-04-19 — search-dropdown: default `hx-target` uses HTMX `global #…` so fragment swaps resolve from the document when the trigger is inside shadow DOM.
2026-04-19 — Permission group portal: dual-listbox users/permissions + `list_kind="user"`; standard `card` layout (no `<details>`) to fix overlap; `_dual_listbox`: `is-multiline`, `is-align-items-flex-start`, `icon-text` labels (Assign, Remove, Assign all, Remove all) on user edit and permission group.
