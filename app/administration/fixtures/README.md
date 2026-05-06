# Fixtures

For local development, load all dev fixtures via:

```bash
python manage.py seed_dev
```

This is a thin wrapper that calls `loaddata` on each file below in dependency order.
You can also load them directly:

```bash
python manage.py loaddata dev_auth_groups dev_users dev_ownership dev_user_scope dev_roles
```

## Fixture files

| File | Contents |
| :--- | :--- |
| `dev_auth_groups.json` | 3 `auth.Group` rows (`generic_user`, `generic_manager`, `generic_admin`) with `auth.Permission` M2M via natural keys |
| `dev_users.json` | 3 `auth.User` rows with a fixed `changeme` password hash; group membership by PK |
| `dev_ownership.json` | 2 divisions, 4 organizations, 4 `DivisionOrganisation` links, 8 domains, 8 `OrganizationDomain` links |
| `dev_user_scope.json` | `UserDivision`, `UserOrganization`, `UserDomain` rows (manager → north scope; admin → full scope) |
| `dev_roles.json` | 3 `Role` rows, 3 `RoleItem` links (Role → auth.Group), 3 `UserRole` assignments |

## Notes

- All users have password `changeme`.
- A Django superuser is **not** included. Create one separately: `python manage.py createsuperuser`.
- Fixtures use integer PKs and are designed for a **fresh-migrated empty database**. Run a full DB reset before loading if rows already exist.
- Permission M2M on groups uses natural foreign keys (`[codename, app_label, model]`) to avoid brittleness across DB resets where `auth.Permission` PKs differ.
- Load order is documented in `docs/ARCHITECTURE/SEEDING.md`.
