---
name: delete-database-rebuild-models
description: Runs the repo-root script that deletes project migration files, clears the database, runs makemigrations and migrate, and optionally seed_dev. Use after Django model/schema changes, when resetting dev data, or when the user mentions delete_database_rebuild_models.py, full DB rebuild, or migration reset workflow.
---

# Delete database and rebuild models

## Script

From the **repository root**:

```bash
python delete_database_rebuild_models.py
python delete_database_rebuild_models.py --seed
```

- **`--seed`**: runs `python manage.py seed_dev` after migrations (dev users and sample division/org/ownership data; see `docs/users_and_passwords.md`).

## What it does

1. Walks each `app/<application>/migrations/` directory (every direct child of `app/` that contains a `migrations` folder), deletes **all files** there except `__init__.py`, and removes `__pycache__` if present.
2. Clears the database (SQLite file removal, or PostgreSQL `DROP SCHEMA public CASCADE` + `CREATE SCHEMA public` when using `DATABASE_URL` with Postgres).
3. Runs `makemigrations` then `migrate`.
4. Optionally runs `seed_dev`.

## Agent notes

- **Stop** the Django dev server (and anything else using the DB) before running.
- Matches `.cursor/rules/migration-strategy.mdc`: no incremental migrations during active dev; disposable DB + fresh migrations + optional seed.
- Do not add legacy-row cleanup in seeds; rely on this workflow instead.
