from django.db import models

from app.administration.models.auditable_mixin import AuditFieldsMixin


class OrganizationDomain(AuditFieldsMixin):
    """M2M through: an organization references many data domains."""

    organization = models.ForeignKey(
        "Organization",
        on_delete=models.CASCADE,
        related_name="organization_domain_links",
    )
    domain = models.ForeignKey(
        "Domain",
        on_delete=models.CASCADE,
        related_name="organization_domain_links",
    )

    class Meta:
        db_table = "core_organizationdomain"
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "domain"],
                name="uniq_organization_domain",
            ),
        ]
