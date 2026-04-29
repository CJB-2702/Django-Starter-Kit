"""
Compute red/yellow audit warnings for a user's data domain assignments.

Rules (see docs/DOMAIN/admin/DATA_OWNERSHIP.md §6):

- **Red** — domain's organization is NOT among the user's assigned organizations.
- **Yellow** — domain's organization matches but division does NOT (or vice versa).
- **None** — both organization and division match an assignment.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.administration.models import (
    Division,
    Domain,
    DivisionOrganisation,
    OrganizationDomain,
    UserDivision,
    UserOrganization,
)


@dataclass(frozen=True)
class DomainWarning:
    """Per-domain warning level (severity: 'red', 'yellow', or empty string)."""

    domain_id: int
    severity: str
    label: str


def _user_org_ids(user_id: int) -> set[int]:
    return set(
        UserOrganization.objects.filter(user_id=user_id).values_list(
            "organization_id",
            flat=True,
        ),
    )


def _user_division_ids(user_id: int) -> set[int]:
    return set(
        UserDivision.objects.filter(user_id=user_id).values_list("division_id", flat=True),
    )


def _domain_to_orgs() -> dict[int, set[int]]:
    out: dict[int, set[int]] = {}
    for link in OrganizationDomain.objects.all().values_list("domain_id", "organization_id"):
        domain_id, org_id = link
        out.setdefault(domain_id, set()).add(org_id)
    return out


def _org_to_division() -> dict[int, int]:
    out: dict[int, int] = {}
    for link in DivisionOrganisation.objects.all().values_list("organization_id", "division_id"):
        org_id, div_id = link
        out[org_id] = div_id
    return out


def compute_domain_warnings(
    *,
    user_id: int,
    domains: Iterable[Domain],
) -> dict[int, DomainWarning]:
    """
    Build a mapping ``domain_id -> DomainWarning`` for the supplied domains.

    Empty severity ('') means no warning (the domain's organization and division both
    match one of the user's assignments).
    """
    user_org_ids = _user_org_ids(user_id)
    user_division_ids = _user_division_ids(user_id)
    domain_orgs = _domain_to_orgs()
    org_division = _org_to_division()

    out: dict[int, DomainWarning] = {}

    for d in domains:
        org_ids = domain_orgs.get(d.pk, set())
        if not org_ids:
            out[d.pk] = DomainWarning(
                domain_id=d.pk,
                severity="red",
                label="Domain is not linked to any organization.",
            )
            continue

        # Best match: any org both in user_org_ids and matching the user's division
        any_org_match = bool(user_org_ids & org_ids)
        any_division_match = False
        for oid in org_ids:
            div_id = org_division.get(oid)
            if div_id is not None and div_id in user_division_ids:
                any_division_match = True
                break

        if any_org_match and any_division_match:
            out[d.pk] = DomainWarning(domain_id=d.pk, severity="", label="")
        elif any_org_match or any_division_match:
            out[d.pk] = DomainWarning(
                domain_id=d.pk,
                severity="yellow",
                label=(
                    "Organization match without matching division "
                    "(or vice versa)."
                ),
            )
        else:
            out[d.pk] = DomainWarning(
                domain_id=d.pk,
                severity="red",
                label="Domain belongs to an organization the user is not assigned to.",
            )

    return out


def serialize_warnings(warnings: dict[int, DomainWarning]) -> dict[int, dict[str, str]]:
    """Plain-dict version of warnings keyed by domain id (for templates)."""
    return {
        domain_id: {"severity": w.severity, "label": w.label}
        for domain_id, w in warnings.items()
    }
