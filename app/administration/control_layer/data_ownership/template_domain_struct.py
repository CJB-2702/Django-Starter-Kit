from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from django.contrib.auth import get_user_model

from app.administration.models import Domain, DomainTemplate, DomainTemplateItem, UserDomain, UserDomainTemplate

User = get_user_model()


@dataclass
class TemplateDomainStruct:
    """Read aggregate: a user's domain template, expected domains, and explicit assignments."""

    user_id: int
    template_assignment: UserDomainTemplate | None = None
    template: DomainTemplate | None = None
    expected_domain_ids: frozenset[int] = field(default_factory=frozenset)
    actual_domain_ids: frozenset[int] = field(default_factory=frozenset)
    manual_domain_ids: frozenset[int] = field(default_factory=frozenset)

    @property
    def has_template(self) -> bool:
        return self.template is not None

    @classmethod
    def load(cls, user_id: int) -> TemplateDomainStruct:
        user = User.objects.get(pk=user_id)

        try:
            template_assignment = UserDomainTemplate.objects.select_related("template").get(
                user_id=user_id,
                is_active=True,
            )
        except UserDomainTemplate.DoesNotExist:
            template_assignment = None

        actual_domain_ids = frozenset(
            UserDomain.objects.filter(
                user=user,
                is_active=True,
            ).values_list("domain_id", flat=True)
        )

        if template_assignment is None:
            return cls(
                user_id=user_id,
                actual_domain_ids=actual_domain_ids,
                manual_domain_ids=actual_domain_ids,
            )

        template = template_assignment.template
        expected_domain_ids = frozenset(
            DomainTemplateItem.objects.filter(
                template=template,
                is_active=True,
            ).values_list(
                "domain_id",
                flat=True,
            ),
        )

        manual_domain_ids = actual_domain_ids - expected_domain_ids

        return cls(
            user_id=user_id,
            template_assignment=template_assignment,
            template=template,
            expected_domain_ids=expected_domain_ids,
            actual_domain_ids=actual_domain_ids,
            manual_domain_ids=manual_domain_ids,
        )

    def to_dict(self) -> dict[str, Any]:
        domains = Domain.objects.filter(pk__in=self.actual_domain_ids).values("id", "name", "slug")
        domain_list = [
            {
                "id": d["id"],
                "name": d["name"],
                "slug": d["slug"],
                "source": (
                    "template"
                    if d["id"] in self.expected_domain_ids
                    else "manual"
                ),
            }
            for d in domains
        ]
        return {
            "user_id": self.user_id,
            "template": (
                {
                    "id": self.template.pk,
                    "name": self.template.name,
                    "slug": self.template.slug,
                }
                if self.template
                else None
            ),
            "has_template": self.has_template,
            "expected_domain_ids": sorted(self.expected_domain_ids),
            "actual_domain_ids": sorted(self.actual_domain_ids),
            "manual_domain_ids": sorted(self.manual_domain_ids),
            "domains": domain_list,
        }
