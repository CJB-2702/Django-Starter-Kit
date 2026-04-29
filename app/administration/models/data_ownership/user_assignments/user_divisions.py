from django.conf import settings
from django.db import models

from app.administration.models.auditable_mixin import AuditFieldsMixin
from app.administration.models.data_ownership.divisions import Division

from . import ActiveUserAssignmentManager


class UserDivision(AuditFieldsMixin):
    """User membership in a division; soft-remove via is_active."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="user_division_links",
    )
    division = models.ForeignKey(
        Division,
        on_delete=models.CASCADE,
        related_name="user_division_links",
    )
    is_active = models.BooleanField(default=True)

    objects = ActiveUserAssignmentManager()
    all_objects = models.Manager()

    class Meta:
        db_table = "core_userdivision"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "division"],
                name="uniq_user_division",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} → {self.division_id}"
