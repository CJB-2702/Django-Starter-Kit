"""Search and loading functions for domain templates."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db.models import QuerySet

from app.administration.control_layer.data_ownership.template_domain_struct import (
    TemplateDomainStruct,
)
from app.administration.models import DomainTemplate

User = get_user_model()


def list_templates(*, include_inactive: bool = False) -> QuerySet[DomainTemplate]:
    """Load all domain templates (active by default)."""
    qs = DomainTemplate.objects.prefetch_related("items__domain")
    if not include_inactive:
        qs = qs.filter(is_active=True)
    return qs.order_by("name")


def load_user_domain_template_struct(user_id: int) -> TemplateDomainStruct:
    """Load a read-only aggregate of user's domain template and domains."""
    return TemplateDomainStruct.load(user_id)
