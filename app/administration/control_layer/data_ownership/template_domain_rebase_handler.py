"""Handler: sync a user's UserDomain memberships to domain templates (rebase or additive)."""

from __future__ import annotations

from django.contrib.auth import get_user_model

from app.administration.models import Domain, DomainTemplate, DomainTemplateItem, UserDomain

User = get_user_model()


class TemplateDomainRebaseHandler:
    """One complex step: align user.domains with a domain template (rebase or additive)."""

    def __init__(
        self,
        *,
        user: User,
        new_template: DomainTemplate,
        previous_template: DomainTemplate | None,
    ) -> None:
        self.user = user
        self.new_template = new_template
        self.previous_template = previous_template

    @staticmethod
    def _template_domain_ids(template: DomainTemplate | None) -> set[int]:
        if template is None:
            return set()
        return set(
            DomainTemplateItem.objects.filter(
                template=template,
                is_active=True,
            ).values_list(
                "domain_id",
                flat=True,
            ),
        )

    def rebase(self) -> None:
        """Remove domains from previous template and apply new template's domains."""
        previous_ids = self._template_domain_ids(self.previous_template)
        new_ids = self._template_domain_ids(self.new_template)

        current_user_domains = set(
            UserDomain.objects.filter(
                user=self.user,
                is_active=True,
            ).values_list("domain_id", flat=True)
        )

        if previous_ids:
            to_remove = previous_ids - new_ids
            if to_remove:
                UserDomain.objects.filter(
                    user=self.user,
                    domain_id__in=to_remove,
                    is_active=True,
                ).update(is_active=False)

        to_add = new_ids - current_user_domains
        if to_add:
            domains = Domain.objects.filter(pk__in=to_add)
            for domain in domains:
                UserDomain.objects.get_or_create(
                    user=self.user,
                    domain=domain,
                    defaults={"is_active": True},
                )

    def additive(self) -> None:
        """Apply new template's domains without removing previous template's domains."""
        new_ids = self._template_domain_ids(self.new_template)
        current_user_domains = set(
            UserDomain.objects.filter(
                user=self.user,
                is_active=True,
            ).values_list("domain_id", flat=True)
        )

        to_add = new_ids - current_user_domains
        if to_add:
            domains = Domain.objects.filter(pk__in=to_add)
            for domain in domains:
                UserDomain.objects.get_or_create(
                    user=self.user,
                    domain=domain,
                    defaults={"is_active": True},
                )
