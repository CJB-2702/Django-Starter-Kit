from django.db import models

from app.administration.models.auditable_mixin import AuditFieldsMixin


class PermissionGroupTemplate(AuditFieldsMixin):
    """Named bundle of permission groups (auth.Group) representing a role profile. DEPRECATED: Use Role instead."""

    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "core_permissiongrouptemplate"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
