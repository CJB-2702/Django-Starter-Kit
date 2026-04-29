from django.db import models

from app.administration.models.auditable_mixin import AuditFieldsMixin
from app.administration.models.data_ownership.domains import Domain


class DomainTemplateItem(AuditFieldsMixin):
    """Through table linking a DomainTemplate to a Domain, with soft-delete for audit trail."""

    template = models.ForeignKey(
        "DomainTemplate",
        on_delete=models.CASCADE,
        related_name="items",
    )
    domain = models.ForeignKey(
        Domain,
        on_delete=models.CASCADE,
        related_name="+",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "core_domaintemplateitem"
        constraints = [
            models.UniqueConstraint(
                fields=["template", "domain"],
                condition=models.Q(is_active=True),
                name="uniq_template_domain_active",
            ),
        ]
