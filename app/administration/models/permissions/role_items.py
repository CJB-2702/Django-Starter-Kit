from django.contrib.auth.models import Group
from django.db import models

from app.administration.models.auditable_mixin import AuditFieldsMixin


class RoleItem(AuditFieldsMixin):
    """Through table linking a Role to an auth.Group."""

    role = models.ForeignKey(
        "Role",
        on_delete=models.CASCADE,
        related_name="items",
    )
    permission_group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name="+",
    )

    class Meta:
        db_table = "core_roleitem"
        constraints = [
            models.UniqueConstraint(
                fields=["role", "permission_group"],
                name="uniq_role_permission_group",
            ),
        ]
