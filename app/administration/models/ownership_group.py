from django.db import models

from app.administration.models.audit import AuditFieldsMixin


class OwnershipGroup(AuditFieldsMixin):
    """Atomic scope for data rows and user assignment."""

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)

    class Meta:
        db_table = "core_ownershipgroup"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
