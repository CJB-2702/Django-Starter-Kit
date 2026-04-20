from django.db import models

from app.administration.models.audit import AuditFieldsMixin


class OrganizationOwnershipGroup(AuditFieldsMixin):
    """M2M through: an organization references many ownership groups."""

    organization = models.ForeignKey(
        "Organization",
        on_delete=models.CASCADE,
        related_name="organization_ownership_links",
    )
    ownership_group = models.ForeignKey(
        "OwnershipGroup",
        on_delete=models.CASCADE,
        related_name="organization_ownership_links",
    )

    class Meta:
        db_table = "core_organizationownershipgroup"
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "ownership_group"],
                name="uniq_org_ownership_group",
            ),
        ]
