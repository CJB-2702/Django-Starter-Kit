from django.db import models

from app.administration.models.audit import AuditFieldsMixin


class DivisionOrganisation(AuditFieldsMixin):
    """Through table: each organization sits in exactly one division."""

    division = models.ForeignKey(
        "Division",
        on_delete=models.PROTECT,
        related_name="division_organization_links",
    )
    organization = models.ForeignKey(
        "Organization",
        on_delete=models.CASCADE,
        related_name="division_organization_links",
    )

    class Meta:
        db_table = "core_divisionorganisation"
        constraints = [
            models.UniqueConstraint(
                fields=["organization"],
                name="uniq_division_org_one_division_per_org",
            ),
        ]
