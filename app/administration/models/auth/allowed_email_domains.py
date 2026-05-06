from django.db import models
from app.administration.models.auditable_mixin import AuditFieldsMixin


class AllowedEmailDomain(AuditFieldsMixin, models.Model):
    domain = models.CharField(max_length=255, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "core_allowedemaildomains"

    def __str__(self):
        return self.domain
