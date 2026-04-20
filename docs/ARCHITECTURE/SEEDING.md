# Seeding plan: Django fixtures

This document defines **where fixture files live**, **how to author them**, and **rules** that stay consistent with `MODEL_PATTERNS.md`, `LAYER_RULES.md`, and `ARCHITECTURE.md`. It applies to **JSON/YAML/XML fixtures** loaded with `manage.py loaddata`.

## 1. Purpose and scope

| Use case | Fixtures appropriate? | Notes |
| :--- | :--- | :--- |
| **Local dev / demo** | Yes | Repeatable baseline data (roles, reference lists, sample rows). |
| **Automated tests** | Often yes | Small, stable datasets; prefer **minimal** fixtures or factories where speed matters. |
| **Production** | Rarely | Prefer migrations (`RunPython`), one-off ops, or ETL—not checked-in dumps of real data. |

**Fixtures are data snapshots**, not business logic. They **do not** replace the control layer for user-driven writes; they **bootstrap** the database to a known state.

## 2. Where fixtures live in the architecture

Django discovers fixtures under each app’s **`fixtures/`** directory (app root, sibling to `models/`, `migrations/`, `management/`).

```text
<sub-application>/
├── fixtures/                 # ← seed data for this Django app only
│   ├── README.md             # optional: describe load order / intent
│   ├── reference_data.json   # example: lookup tables, permissions bundles
│   └── demo_maintenance.json # example: slice-specific demo rows
├── migrations/
├── management/
│   └── commands/             # optional: thin wrappers that call loaddata (see §6)
├── models/
├── presentation_layer/
└── control_layer/
```

**Rules:**

- **Co-locate with ownership:** put a fixture in the **same Django app** that owns the models it serializes. Cross-app FKs are fine in one file, but avoid one giant project-wide dump unless you intentionally maintain a “full stack” seed.
- **Not in `control_layer/` or `presentation_layer/`:** seed files are **infrastructure**, like `migrations/`—see `ARCHITECTURE.md` §5.
- **Optional project-level bundle:** if you need a single command to load everything, add a **management command** at the project or a dedicated “bootstrap” app that loads named fixtures **in order** (§6)—do not invent a parallel `seed_data/` tree that Django’s loader ignores unless you document a custom loader.

## 3. File naming and granularity

- Use **lowercase snake_case** and a **clear intent**: `rbac_groups_permissions.json`, `asset_categories.json`, `demo_work_orders.json`.
- Prefer **several smaller fixtures** over one monolith: easier reviews, selective loads, and clearer ownership per app.
- If order matters, encode it in **documentation** (fixture `README` or this file) and/or a **management command** that runs `loaddata` in sequence—Django does **not** auto-order multiple files beyond the order you pass on the CLI.

## 4. Authoring rules (patterns)

### 4.1 Primary keys and stability

- **Prefer natural keys** when models define `Meta.unique_together` / `natural_key()` and you want merges across environments to be stable. Export with `dumpdata --natural-foreign --natural-primary` when applicable.
- **Integer PKs** in fixtures are acceptable for **throwaway dev DBs**; they are **fragile** when mixed with auto-increment state—document that the DB should be migrated fresh before load, or use natural keys.
- **Never hand-edit** sequences in PostgreSQL/SQLite to “fix” a fixture; regenerate from a clean DB or switch to natural keys.

### 4.2 Foreign keys and load order

- Rows must appear **before** dependents: parent model instances before children referencing them.
- For **circular** dependencies, split into **two fixtures** loaded in order, or use **natural keys** so Django can resolve in one pass where supported.
- **Swappable user model:** load **auth-related** data (groups, permissions) in fixtures that run after **user rows** exist, or load users first in the same file in top-to-bottom order.

### 4.3 Many-to-many and “through” models

- Prefer explicit **through model** rows in JSON when the M2M uses a custom through table.
- For simple M2M, Django’s serialized form may embed relations—match the output of `dumpdata` for your model once and reuse that shape.

### 4.4 Audit and trace fields (`MODEL_PATTERNS.md`)

Models that require **`created_at` / `updated_at` / `created_by_id` / `updated_by_id`** should be seeded with **explicit values** in fixtures:

- Use **fixed timestamps** for reproducibility (e.g. ISO 8601 strings Django accepts).
- Point **`created_by_id` / `updated_by_id`** at real user PKs that exist **earlier** in the same fixture or in a prerequisite fixture (e.g. a `seed_users.json` loaded first).

Do not rely on `auto_now_add` alone without values in the fixture—serialized rows should include the fields your schema expects.

### 4.5 Permissions and RBAC

- Prefer loading **`auth.Group`**, **`auth.Permission`**, and group-permission links via fixtures **owned by the app that defines the custom permissions** (usually where permissions are created in migrations).
- Keep permission codenames **aligned with migration definitions** so `loaddata` does not reference stale names.

### 4.6 Content types and generic relations

- Fixtures that reference **`ContentType`** are **brittle** across DBs if IDs differ. Prefer:
  - avoiding generic FKs in seed data, or
  - loading contenttypes in a known order and matching your migration state, or
  - using natural keys for contenttypes if you standardize on that approach.

### 4.7 Secrets and PII

- **No secrets** (API keys, tokens) in committed fixtures.
- **No real PII**; use obvious placeholders for demo users and contacts.

## 5. Workflow: create, review, load

**Generate from truth (recommended):**

1. Migrate a **clean** database.
2. Create rows via Django shell, admin, or **control-layer** helpers (respects invariants).
3. `python manage.py dumpdata <app_label.ModelName> ... --natural-foreign --natural-primary -o app/fixtures/name.json`
4. Review diff; strip noise; keep files small.

**Load:**

```bash
python manage.py loaddata reference_data demo_maintenance
```

Use **fixture labels without** `.json` when invoking `loaddata` (Django resolves extensions).

**CI / fresh dev:**

- Document prerequisite order (e.g. `auth` groups before app-specific rows).
- Fail fast: if a fixture references missing FK targets, fix order or split files.

## 6. Management commands (optional)

Use `management/commands/` **only** to orchestrate loading:

- Parse arguments, print intent, call `call_command("loaddata", ...)` in order, or document the same in a Makefile/task.
- **Do not** embed large imperative seed logic that duplicates the control layer—if business rules matter, prefer **`RunPython`** in migrations or a dedicated **`seed_demo`** command that calls **control layer** functions for a few high-value rows, and use **fixtures** only for static reference data.

This mirrors `ARCHITECTURE.md`: management commands stay **thin**; complex writes belong in **`control_layer/`**.

## 7. Testing

- **`TransactionTestCase`** / fixtures: suitable when you need DB reset per test class; can be slow.
- Prefer **`pytest-django`** with **`django_db`** and small fixtures, or **factory_boy** for per-test data, when tests need **variation** more than a frozen snapshot.
- Keep **test-only** fixture files under the same app `fixtures/` but name them clearly (`test_users.json`) or load explicitly in tests to avoid accidental dev loads.

## 8. Checklist before merging a new fixture

- [ ] Lives under the **owning app’s** `fixtures/`.
- [ ] Load order documented if dependencies span files or apps.
- [ ] Audit/user FK fields populated per `MODEL_PATTERNS.md`.
- [ ] No secrets or real PII.
- [ ] Regenerated or validated against current migrations.
- [ ] `loaddata` run succeeds on empty DB after `migrate`.

---

**Summary:** Treat **`fixtures/`** as **versioned, app-local bootstrap data** at the Django app root; author with **`dumpdata`** and natural keys where possible; keep files **small and intentional**; use **management commands** only to sequence loads; reserve **control layer** for real workflows, not for routine static reference seeds.
