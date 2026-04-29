from django.conf import settings
from django.db import models

from app.administration.models.auditable_mixin import AuditFieldsMixin
from app.administration.models.data_ownership.organization import Organization

from . import ActiveUserAssignmentManager


class UserOrganization(AuditFieldsMixin):
    """User membership in an organization; soft-remove via is_active."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="user_organization_links",
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="user_organization_links",
    )
    is_active = models.BooleanField(default=True)

    objects = ActiveUserAssignmentManager()
    all_objects = models.Manager()

    class Meta:
        db_table = "core_userorganization"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "organization"],
                name="uniq_user_organization",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} → {self.organization_id}"
