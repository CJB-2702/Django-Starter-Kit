from django.db import models

from app.administration.models.auditable_mixin import AuditFieldsMixin


class Domain(AuditFieldsMixin):
    """Atomic row-level access scope. Every scoped data row carries exactly one domain."""

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)

    class Meta:
        db_table = "core_domain"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
