from django.contrib.auth.models import Group
from django.db import models

from app.administration.models.auditable_mixin import AuditFieldsMixin


class PermissionGroupTemplateItem(AuditFieldsMixin):
    """Through table linking a PermissionGroupTemplate to an auth.Group."""

    template = models.ForeignKey(
        "PermissionGroupTemplate",
        on_delete=models.CASCADE,
        related_name="items",
    )
    permission_group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name="+",
    )

    class Meta:
        db_table = "core_permissiongrouptemplateitem"
        constraints = [
            models.UniqueConstraint(
                fields=["template", "permission_group"],
                name="uniq_template_permission_group",
            ),
        ]
