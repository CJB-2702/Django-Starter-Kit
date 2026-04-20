from django.db import models

from app.administration.models.audit import AuditFieldsMixin


class Division(AuditFieldsMixin):
    """Top-level grouping of organizations (e.g. regional or business division)."""

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)

    class Meta:
        db_table = "core_division"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
