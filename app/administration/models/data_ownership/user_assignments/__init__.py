from django.db import models


class ActiveUserAssignmentManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(disabled=False)


from .user_divisions import UserDivision
from .user_organizations import UserOrganization
from .user_ownership_groups import UserOwnershipGroup

__all__ = [
    "ActiveUserAssignmentManager",
    "UserDivision",
    "UserOrganization",
    "UserOwnershipGroup",
]
