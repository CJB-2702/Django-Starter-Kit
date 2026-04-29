from django.conf import settings
from django.db import models

from app.administration.models.auditable_mixin import AuditFieldsMixin


class UserRole(AuditFieldsMixin):
    """User assignment of a Role, with relationship type and justification notes."""

    class RelationshipType(models.TextChoices):
        PRIMARY = "primary", "Primary role"
        SPECIALTY = "specialty", "Specialty/specialization"
        SIDE_JOB = "side_job", "Side job"
        FOR_FUN = "for_fun", "For learning/fun"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="user_role_links",
    )
    role = models.ForeignKey(
        "Role",
        on_delete=models.CASCADE,
        related_name="user_assignment_links",
    )
    relationship_type = models.CharField(
        max_length=20,
        choices=RelationshipType.choices,
        default=RelationshipType.PRIMARY,
    )
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "core_userrole"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "role"],
                name="uniq_user_role",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} → {self.role_id}"
