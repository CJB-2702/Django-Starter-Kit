from django.conf import settings
from django.db import models

from app.administration.models.auditable_mixin import AuditFieldsMixin
from app.administration.models.data_ownership.user_assignments import (
    ActiveUserAssignmentManager,
)


class UserPermissionGroupTemplate(AuditFieldsMixin):
    """Active permission group template assignment for a user, with justification notes."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="user_permission_group_template_links",
    )
    template = models.ForeignKey(
        "PermissionGroupTemplate",
        on_delete=models.PROTECT,
        related_name="user_assignment_links",
    )
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    objects = ActiveUserAssignmentManager()
    all_objects = models.Manager()

    class Meta:
        db_table = "core_userpermissiongrouptemplate"
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(is_active=True),
                name="uniq_active_user_permission_group_template",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} → {self.template_id}"
