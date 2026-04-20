# Fixtures

For local development, prefer the management command:

```bash
python manage.py seed_dev
```

It creates `generic_user`, `generic_manager`, and `generic_admin`, role groups, and sample division / organization / ownership group rows. Set `SEED_USER_PASSWORD` for passwords (default `changeme`).

Optional JSON fixtures can be added here for static reference data; load order is documented in `docs/ARCHITECTURE/SEEDING.md`.
