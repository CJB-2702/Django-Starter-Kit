from django.conf import settings
from django.db import models

from app.administration.models.auditable_mixin import AuditFieldsMixin
from app.administration.models.ownership_groups.ownership_group import OwnershipGroup

from . import ActiveUserAssignmentManager


class UserOwnershipGroup(AuditFieldsMixin):
    """User membership in an ownership group; soft-remove via disabled."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="user_ownership_group_links",
    )
    ownership_group = models.ForeignKey(
        OwnershipGroup,
        on_delete=models.CASCADE,
        related_name="user_ownership_group_links",
    )
    disabled = models.BooleanField(default=False)

    objects = ActiveUserAssignmentManager()
    all_objects = models.Manager()

    class Meta:
        db_table = "core_userownershipgroup"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "ownership_group"],
                name="uniq_user_ownership_group",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} → {self.ownership_group_id}"
