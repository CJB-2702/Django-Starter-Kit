from django.conf import settings
from django.db import models

from app.administration.models.auditable_mixin import AuditFieldsMixin
from app.administration.models.data_ownership.domains import Domain

from . import ActiveUserAssignmentManager


class UserDomain(AuditFieldsMixin):
    """User membership in a data domain; soft-remove via is_active."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="user_domain_links",
    )
    domain = models.ForeignKey(
        Domain,
        on_delete=models.CASCADE,
        related_name="user_domain_links",
    )
    is_active = models.BooleanField(default=True)

    objects = ActiveUserAssignmentManager()
    all_objects = models.Manager()

    class Meta:
        db_table = "core_userdomain"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "domain"],
                name="uniq_user_domain",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} → {self.domain_id}"
