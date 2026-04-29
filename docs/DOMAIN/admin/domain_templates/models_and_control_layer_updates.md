# Domain Templates — Models and Control-Layer Plan

This is the **architectural plan** for adding domain templates to the administration app. It describes the **shape** of the new models, the **boundaries** between layers, and the **classes** that need to exist — but not every method signature. For business rules and intent, see [concept.md](concept.md).

---

## 1. Placement

Domain template code lives under the `data_ownership` family of folders that already exists:

```
app/administration/
  models/
    data_ownership/
      domains.py                                ← existing (renamed from ownership_groups.py)
      domain_templates.py                       ← new: DomainTemplate model
      domain_template_items.py                  ← new: DomainTemplateItem (template ↔ domain)
      user_assignments/
        user_domains.py                         ← existing (renamed from user_ownership_groups.py)
      group_relationships/
        organization_domains.py                 ← existing (renamed from organisation_domains.py)
      __init__.py                               ← exports updated
  control_layer/
    data_ownership/
      domain_template_context.py                ← new: DomainTemplateContext (template edits)
      user_domain_assignment_context.py         ← existing name updated; handles domain assignment/rebase
      template_rebase_handler.py                ← new: TemplateDomainRebaseHandler (sync step)
      template_domain_struct.py                 ← new: TemplateDomainStruct (actual vs. expected)
      domain_assignment_policy.py               ← existing; updated with template rules
      __init__.py                               ← exports updated
  presentation_layer/
    entrypoints/
      data_ownership/
        domain_template_portal.py               ← new: list + detail + edit for templates
        user_domain_assignment.py               ← new: POST routes from user portal for template ops
      __init__.py                               ← exports updated
    search/
      domain_templates.py                       ← new: loaders / querysets for template lists
      user_access.py                            ← new/existing: domain warning helpers
  templates/
    data_ownership_portal/                      ← new (domain template list, detail, edit)
      domain_templates/
        index.html
        detail.html
        _template_row.html
        _items_panel.html
        _assigned_users_panel.html
    user_portal/
      _domain_template_block.html               ← new include: shows current template + domains
```

---

## 2. Model layer

Three models, all under `app/administration/models/data_ownership/`. All three use `AuditFieldsMixin` (created_at, updated_at, created_by, updated_by).

### 2.1 `DomainTemplate`

- File: `domain_templates.py`.
- Class suffix: none (this is a domain aggregate root).
- Fields:
  - `name` — unique, human-readable (e.g., "Facility 1 Transportation").
  - `slug` — unique identifier for URLs and code references.
  - `description` — long text, optional.
  - `is_active` — boolean; inactive templates are hidden from assignment dropdowns but remain for historical assignments.
- Meta:
  - `db_table = "core_domaintemplate"`.
  - `ordering = ["name"]`.
  - Unique constraint on `slug`.

### 2.2 `DomainTemplateItem`

- File: `domain_template_items.py`.
- Through-table linking a domain template to `Domain` rows.
- Fields:
  - `template` — FK to `DomainTemplate`, `related_name="items"`.
  - `domain` — FK to `Domain`, `related_name="+"` (no reverse access needed from domain side).
  - Audit fields: `created_at`, `updated_at`, `created_by`, `updated_by` (tracks historical changes).
  - `is_active` — soft-delete flag; inactive items remain for audit trail.
- Meta:
  - `db_table = "core_domaintemplate_item"`.
  - Unique constraint on `(template, domain)` where `is_active=True` (allow soft-deleted duplicates for history).

### 2.3 `UserDomainTemplate`

- File: `user_domain_templates.py` (under `user_assignments/`).
- Records which domain template is actively assigned to a user. Uses the same soft-remove via `is_active` pattern as `UserDomain`.
- Fields:
  - `user` — FK to `AUTH_USER_MODEL`.
  - `template` — FK to `DomainTemplate`.
  - `is_active` — boolean; soft-remove, mirrors the `UserDomain` pattern.
  - Audit fields: `created_at`, `updated_at`, `created_by`, `updated_by`.
- Managers:
  - `objects = ActiveUserAssignmentManager()` (filters out inactive rows) — reuse the same manager data_ownership family defines.
  - `all_objects = models.Manager()`.
- Meta:
  - `db_table = "core_userdomaintemplate"`.
  - Constraint: at most **one** active (non-inactive) assignment per user.
    - Implemented as a **partial unique index** on `(user,)` where `is_active=True`.

---

## 3. Control layer

Control-layer classes under `app/administration/control_layer/data_ownership/` follow the project's [OOP_CONTROL_PATTERNS.md](../../../ARCHITECTURE/OOP_CONTROL_PATTERNS.md) vocabulary.

### 3.1 `DomainTemplateContext`

- File: `domain_template_context.py`.
- Role: **Context** for edits to a single domain template (id-keyed or slug-keyed).
- Responsibilities:
  - Load a read struct describing the template, its items, and historical changes.
  - Add / remove domains (delegating any policy checks to `DomainAssignmentPolicy`).
  - Activate / deactivate the template.
  - Expose the historical audit trail of item additions/removals.
- Does **not** directly mutate `UserDomain` rows; that belongs to the user-side assignment context below.

### 3.2 `UserDomainAssignmentContext`

- File: `user_domain_assignment_context.py` (renamed/extended from existing code).
- Role: **Context** for a user's active domain template — assign, rebase, swap, disable.
- Responsibilities:
  - Assign a domain template to the user (creates/reactivates `UserDomainTemplate`).
  - Swap domain templates (default rebase; optional additive).
  - Disable the current domain template assignment.
  - Add/remove explicit `UserDomain` assignments (outside the template footprint).
- Delegates the heavy "update actual `user.domains` membership" step to `TemplateDomainRebaseHandler`.

### 3.3 `TemplateDomainRebaseHandler`

- File: `template_rebase_handler.py`.
- Role: **Handler** (a single complex step — the domain membership sync).
- Responsibilities:
  - Compute the **previous** domain template's domain set (if any previous assignment exists, even if inactive).
  - Compute the **new** domain template's domain set.
  - In **rebase** mode: `user.domains = (current - previous_template_domains) ∪ new_template_domains`.
  - In **additive** mode: `user.domains |= new_template_domains` (no removal).
  - Update the session snapshot (`user_domain_ids`) after changes.
- Operates inside an existing transaction; does not open its own.

### 3.4 `TemplateDomainStruct`

- File: `template_domain_struct.py`.
- Role: **Struct** — read-only aggregate for display and audit.
- Fields (conceptual):
  - `user_id`
  - `template` — the currently assigned domain template (or `None`).
  - `expected_domain_ids` — from the template's items.
  - `actual_domain_ids` — from the user's `UserDomain` rows.
  - `manual_domain_ids` — domains the user holds explicitly outside the template.
  - `has_template_assignment` — bool.
- Exposes a `to_dict()` method for template rendering, following [OOP_CONTROL_PATTERNS.md §2](../../../ARCHITECTURE/OOP_CONTROL_PATTERNS.md).

### 3.5 `DomainAssignmentPolicy`

- File: `domain_assignment_policy.py` (existing; updated with template rules).
- Role: **Guard → Policy**.
- Responsibilities:
  - `assert_actor_may_assign_template(actor, template)` — admins always pass; others must have access to all domains in the template.
  - `assert_actor_may_edit_template(actor)` — admins-only by default.
  - `assert_actor_may_assign_domains(actor, domains)` — actor may only assign domains from their own domain template.
- Lives in the data_ownership family so all domain-grant rules are co-located.

---

## 4. Presentation layer

### 4.1 Entrypoints

Two URL-bound entrypoints under `app/administration/presentation_layer/entrypoints/data_ownership/`:

- **`domain_template_portal`**
  - GET list at `/administration/domain-templates/`.
  - GET detail + edit at `/administration/domain-templates/<slug>/`.
  - POST actions: create / rename / deactivate template; add / remove items.
- **`user_domain_assignment`**
  - POST from the user-portal edit screen.
  - Actions: `assign_domain_template` (with notes), `rebase_domain_template`, `set_additive_layer`, `disable_domain_template`, `assign_manual_domain`, `revoke_manual_domain`.
- Routes are registered in [`app/administration/urls.py`](../../../../app/administration/urls.py). URL namespace follows the existing `domain_portal` convention.

### 4.2 Search / loaders

- `presentation_layer/search/domain_templates.py`:
  - `list_templates(user, *, include_inactive=False)` — admin-scoped by `is_admin_actor`.
  - `load_user_domain_template_struct(user_id)` — wraps `TemplateDomainStruct` for easy template rendering.

- `presentation_layer/search/user_access.py`:
  - `compute_domain_warnings(user)` — audit warning colors (red/yellow) for cross-org/cross-division grants.

### 4.3 Templates (HTML)

Under `app/administration/templates/data_ownership_portal/domain_templates/`:

- `index.html` — list templates with counts of items and assignees.
- `detail.html` — one template's items and assignees.
- Partials for HTMX panels in the project's `_panel.html` / `_append.html` convention ([HTMX_PATTERNS.md](../../../ARCHITECTURE/HTMX_PATTERNS.md)).

Under `app/administration/templates/user_portal/`:

- `_domain_template_block.html` — shown on the user edit screen.
  - Top row: current domain template name (if assigned).
  - Secondary row: list of domains the user can access (grouped: `[Template]` vs. `[Manual]`).
  - Expiration indicators for explicit assignments.
  - Actions: assign a different template, re-rebase, disable.

### 4.4 Domain warning integration (user portal)

The user portal renders **domain audit warnings** (see [DATA_OWNERSHIP.md §6](../DATA_OWNERSHIP.md)):

- **Red** — domain's organization ∉ user's organizations.
- **Yellow** — organization matches but division does not (or vice versa).

Each domain in the user's accessible list gets a colored tag. The comparison is computed by `compute_domain_warnings(user)` in `presentation_layer/search/user_access.py`.

---

## 5. Session

The existing `auth_session.refresh_auth_in_session` snapshot continues to store:

- `user_domain_ids` — **all** domain ids the user can access (from template + explicit assignments), computed fresh at every login or explicit rebase.
- `user_permission_codenames` — all permission codenames from the user's active permission groups.

No domain template information is stored in the session — the snapshot is pure capability and domain state, and the template is a label for how that state was constructed, not a runtime filter.

**Important for performance:** Every route that filters by domain queries against the session snapshot `user_domain_ids`, not the database. Permission checks query `user_permission_codenames`.

---

## 6. Seed data (`seed_dev`)

The seed command gains a small block creating 2–3 domain templates (examples):

- **`facility_1`** — bundles facility_1_transportation, facility_1_supply.
- **`cross_site`** — bundles all facilities + headquarters.

Existing seeded users are assigned matching templates so developer environments demonstrate the full flow from day one.

---

## 7. Audit history and soft-delete

Every change to `DomainTemplateItem` is auditable:

- **Addition**: New row created with `created_by`, `created_at`.
- **Removal**: Row marked `is_active=False` instead of deleted; retains all audit context.
- **Historical view**: A detail/audit page shows all items ever added to the template, with status (active/removed), timestamps, and actor.

This allows operators to see *when* a domain was added to a template and *who* made the change — crucial for understanding permission drift and explaining scope changes.

---

## 8. URL map (after this change)

```
/administration/domain-templates/                    (new — list)
/administration/domain-templates/<slug>/             (new — detail + edit)
POST /administration/user-portal/<user_id>/domains/  (new — assign/rebase/etc.)
/administration/domains/<id>/                        (existing — domain detail)
```

---

## 9. Out of scope for this document

- Exact method signatures, line-by-line code, or test plans.
- UI copy and exact Bulma class choices.
- Object-permission packages (django-guardian etc.) — not used.
- Per-route decorators — those are picked up from the existing `domain_assignment_policy` conventions.

---

## Related documents

- [concept.md](concept.md) — business concept and rules (source of truth for *what* domain templates are).
- [../DATA_OWNERSHIP.md](../DATA_OWNERSHIP.md) — the Data Domain primitive and the Golden Rule.
- [../RBAC.md](../RBAC.md) — Django permission system and permission group templates (orthogonal system).
- [../USERS.md](../USERS.md) — user model concerns, session shape, auditing.
- [../../../ARCHITECTURE/OOP_CONTROL_PATTERNS.md](../../../ARCHITECTURE/OOP_CONTROL_PATTERNS.md) — class-suffix vocabulary.
- [../../../ARCHITECTURE/LAYER_RULES.md](../../../ARCHITECTURE/LAYER_RULES.md) — reads vs. writes.
- [../../../ARCHITECTURE/HTMX_PATTERNS.md](../../../ARCHITECTURE/HTMX_PATTERNS.md) — list/panel/append partial convention.
