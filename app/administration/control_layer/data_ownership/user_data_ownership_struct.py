from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from django.contrib.auth import get_user_model

from app.administration.models import Division, Domain, Organization

User = get_user_model()


@dataclass
class UserDataOwnershipStruct:
    """
    Aggregated read model for a user's active division, organization, and data
    domain assignments (non-disabled rows only).
    """

    user_id: int
    divisions: list[Division] = field(default_factory=list)
    organizations: list[Organization] = field(default_factory=list)
    domains: list[Domain] = field(default_factory=list)

    @classmethod
    def load(cls, user_id: int, *, eager: bool = True) -> UserDataOwnershipStruct:
        """Load assignment rows; ``eager`` reserved for future selective loading."""
        _ = eager
        user = User.objects.get(pk=user_id)
        from app.administration.models import UserDivision, UserDomain, UserOrganization

        div_ids = UserDivision.objects.filter(user=user).values_list("division_id", flat=True)
        org_ids = UserOrganization.objects.filter(user=user).values_list(
            "organization_id",
            flat=True,
        )
        domain_ids = UserDomain.objects.filter(user=user).values_list("domain_id", flat=True)

        divisions = list(Division.objects.filter(pk__in=div_ids).order_by("name"))
        organizations = list(
            Organization.objects.filter(pk__in=org_ids)
            .order_by("divisions__name", "name")
            .prefetch_related("divisions"),
        )
        domains = list(Domain.objects.filter(pk__in=domain_ids).order_by("name"))
        return cls(
            user_id=user_id,
            divisions=divisions,
            organizations=organizations,
            domains=domains,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "divisions": [{"id": d.pk, "name": d.name, "slug": d.slug} for d in self.divisions],
            "organizations": [
                {
                    "id": o.pk,
                    "name": o.name,
                    "slug": o.slug,
                    "division_id": o.division_id,
                }
                for o in self.organizations
            ],
            "domains": [{"id": d.pk, "name": d.name, "slug": d.slug} for d in self.domains],
        }
