from django.db import models


class ActiveUserAssignmentManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


from .user_divisions import UserDivision
from .user_domain_templates import UserDomainTemplate
from .user_domains import UserDomain
from .user_organizations import UserOrganization

__all__ = [
    "ActiveUserAssignmentManager",
    "UserDivision",
    "UserDomain",
    "UserDomainTemplate",
    "UserOrganization",
]
