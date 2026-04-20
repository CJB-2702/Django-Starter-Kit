"""Role group names aligned with seeded Django ``Group`` rows."""

GROUP_GENERIC_USER = "generic_user"
GROUP_GENERIC_MANAGER = "generic_manager"
GROUP_GENERIC_ADMIN = "generic_admin"

# Product language: Django's built-in ``auth.Group`` model (database table ``auth_group``)
# is referred to in UI copy and docs as **permission groups** to avoid confusion with
# application ownership groups (``OwnershipGroup`` / ``core_ownershipgroup``).
DJANGO_GROUP_UI_NAME = "permission group"
DJANGO_GROUPS_UI_NAME = "permission groups"
