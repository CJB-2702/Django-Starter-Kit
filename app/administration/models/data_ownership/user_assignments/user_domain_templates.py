from django.conf import settings
from django.db import models

from app.administration.models.auditable_mixin import AuditFieldsMixin
from app.administration.models.data_ownership.user_assignments import (
    ActiveUserAssignmentManager,
)


class UserDomainTemplate(AuditFieldsMixin):
    """User assignment of an active domain template."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="user_domain_template_links",
    )
    template = models.ForeignKey(
        "DomainTemplate",
        on_delete=models.PROTECT,
        related_name="user_assignment_links",
    )
    is_active = models.BooleanField(default=True)

    objects = ActiveUserAssignmentManager()
    all_objects = models.Manager()

    class Meta:
        db_table = "core_userdomaintemplate"
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(is_active=True),
                name="uniq_active_user_domain_template",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} → {self.template_id}"
