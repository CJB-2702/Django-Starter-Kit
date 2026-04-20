from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from django.contrib.auth import get_user_model

from app.administration.models import Division, Organization, OwnershipGroup

User = get_user_model()


@dataclass
class UserOwnershipStruct:
    """
    Aggregated read model for a user's active division, organization, and ownership
    group assignments (non-disabled rows only).
    """

    user_id: int
    divisions: list[Division] = field(default_factory=list)
    organizations: list[Organization] = field(default_factory=list)
    ownership_groups: list[OwnershipGroup] = field(default_factory=list)

    @classmethod
    def load(cls, user_id: int, *, eager: bool = True) -> UserOwnershipStruct:
        """Load assignment rows; ``eager`` reserved for future selective loading."""
        _ = eager
        user = User.objects.get(pk=user_id)
        from app.administration.models import UserDivision, UserOrganization, UserOwnershipGroup

        div_ids = UserDivision.objects.filter(user=user).values_list(
            "division_id",
            flat=True,
        )
        org_ids = UserOrganization.objects.filter(user=user).values_list(
            "organization_id",
            flat=True,
        )
        og_ids = UserOwnershipGroup.objects.filter(user=user).values_list(
            "ownership_group_id",
            flat=True,
        )
        divisions = list(
            Division.objects.filter(pk__in=div_ids).order_by("name"),
        )
        organizations = list(
            Organization.objects.filter(pk__in=org_ids)
            .order_by("divisions__name", "name")
            .prefetch_related("divisions"),
        )
        ownership_groups = list(
            OwnershipGroup.objects.filter(pk__in=og_ids).order_by("name"),
        )
        return cls(
            user_id=user_id,
            divisions=divisions,
            organizations=organizations,
            ownership_groups=ownership_groups,
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
            "ownership_groups": [
                {"id": g.pk, "name": g.name, "slug": g.slug} for g in self.ownership_groups
            ],
        }
