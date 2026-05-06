from django.db import models

from app.administration.models.auditable_mixin import AuditFieldsMixin
from app.administration.models.data_ownership.divisions import Division
from app.administration.models.data_ownership.domain_relationships.organization_domains import (
    OrganizationDomain,
)


class Organization(AuditFieldsMixin):
    """Groups data domains for navigation and reporting; overlap across orgs is allowed."""

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255)

    divisions = models.ManyToManyField(
        Division,
        through="DivisionOrganisation",
        related_name="organizations",
    )

    domains = models.ManyToManyField(
        "Domain",
        through=OrganizationDomain,
        related_name="organizations",
    )

    class Meta:
        db_table = "core_organization"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["slug"],
                name="uniq_organization_slug",
            ),
        ]

    def __str__(self) -> str:
        div = self.divisions.first()
        if div is None:
            return self.name
        return f"{div.name} — {self.name}"

    @property
    def division(self) -> Division | None:
        """Single division membership (enforced by DivisionOrganisation)."""
        return self.divisions.first()

    @property
    def division_id(self) -> int | None:
        div = self.division
        return div.pk if div is not None else None
