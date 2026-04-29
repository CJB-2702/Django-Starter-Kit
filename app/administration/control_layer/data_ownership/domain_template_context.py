from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import transaction

from app.administration.models import Domain, DomainTemplate, DomainTemplateItem

User = get_user_model()


class DomainTemplateContext:
    """Control entry for editing a single domain template (id-keyed)."""

    def __init__(self, template_id: int) -> None:
        self.template_id = template_id
        self._template = DomainTemplate.objects.get(pk=template_id)

    @property
    def template(self) -> DomainTemplate:
        return self._template

    def refresh(self) -> None:
        self._template = DomainTemplate.objects.get(pk=self.template_id)

    @transaction.atomic
    def add_domain(self, *, actor: User, domain_id: int) -> DomainTemplateItem:
        domain = Domain.objects.get(pk=domain_id)
        item, _created = DomainTemplateItem.objects.get_or_create(
            template=self._template,
            domain=domain,
            defaults={"created_by": actor, "updated_by": actor, "is_active": True},
        )
        if not _created and not item.is_active:
            item.is_active = True
            item.updated_by = actor
            item.save(update_fields=["is_active", "updated_at", "updated_by"])
        return item

    @transaction.atomic
    def remove_domain(self, *, actor: User, domain_id: int) -> None:
        try:
            item = DomainTemplateItem.objects.get(
                template=self._template,
                domain_id=domain_id,
                is_active=True,
            )
            item.is_active = False
            item.updated_by = actor
            item.save(update_fields=["is_active", "updated_at", "updated_by"])
        except DomainTemplateItem.DoesNotExist:
            pass

    @transaction.atomic
    def set_active(self, *, actor: User, is_active: bool) -> DomainTemplate:
        self._template.is_active = is_active
        self._template.updated_by = actor
        self._template.save(update_fields=["is_active", "updated_at", "updated_by"])
        return self._template

    @transaction.atomic
    def update_metadata(
        self,
        *,
        actor: User,
        name: str | None = None,
        description: str | None = None,
    ) -> DomainTemplate:
        update_fields: list[str] = ["updated_at", "updated_by"]
        if name is not None:
            self._template.name = name
            update_fields.append("name")
        if description is not None:
            self._template.description = description
            update_fields.append("description")
        self._template.updated_by = actor
        self._template.save(update_fields=update_fields)
        return self._template
