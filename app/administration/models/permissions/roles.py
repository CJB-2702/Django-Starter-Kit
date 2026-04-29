from django.db import models

from app.administration.models.auditable_mixin import AuditFieldsMixin


class Role(AuditFieldsMixin):
    """Named bundle of permission groups (auth.Group) representing a job profile."""

    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    parent_role = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        related_name="child_roles",
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "core_role"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
