from django.contrib.auth.models import AbstractUser

from app.administration.control_layer.permissions.permission_grant_guard import is_admin_actor
from app.administration.models import (
    Division,
    Domain,
    Organization,
    UserDivision,
    UserDomain,
    UserOrganization,
)


def list_divisions(user: AbstractUser):
    qs = Division.objects.order_by("name")
    if is_admin_actor(user):
        return qs
    ids = UserDivision.objects.filter(user=user).values_list("division_id", flat=True)
    return qs.filter(pk__in=ids)


def list_organizations(user: AbstractUser):
    qs = Organization.objects.order_by("divisions__name", "name").prefetch_related("divisions")
    if is_admin_actor(user):
        return qs
    ids = UserOrganization.objects.filter(user=user).values_list("organization_id", flat=True)
    return qs.filter(pk__in=ids)


def list_domains(user: AbstractUser):
    qs = Domain.objects.order_by("name")
    if is_admin_actor(user):
        return qs
    ids = UserDomain.objects.filter(user=user).values_list("domain_id", flat=True)
    return qs.filter(pk__in=ids)
