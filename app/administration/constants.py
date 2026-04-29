"""Role group names aligned with seeded Django ``Group`` rows."""

GROUP_GENERIC_USER = "generic_user"
GROUP_GENERIC_MANAGER = "generic_manager"
GROUP_GENERIC_ADMIN = "generic_admin"

# Product language: Django's built-in ``auth.Group`` model (database table ``auth_group``)
# is referred to in UI copy and docs as **permission group**. The row-level access
# scope formerly called "ownership group" is now the **Data Domain** (model: ``Domain``,
# table: ``core_domain``); see ``docs/DOMAIN/admin/DATA_OWNERSHIP.md``.
DJANGO_GROUP_UI_NAME = "permission group"
DJANGO_GROUPS_UI_NAME = "permission groups"

DOMAIN_UI_NAME = "data domain"
DOMAINS_UI_NAME = "data domains"
