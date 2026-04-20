"""Loaders for user permission and ownership aggregates used by entrypoints."""

from app.administration.control_layer.domain_structs.user_django_permissions_struct import (
    UserDjangoPermissionsStruct,
)
from app.administration.control_layer.domain_structs.user_ownership_struct import (
    UserOwnershipStruct,
)


def load_user_ownership_struct(user_id: int, *, eager: bool = True) -> UserOwnershipStruct:
    return UserOwnershipStruct.load(user_id, eager=eager)


def load_user_django_permissions_struct(user_id: int) -> UserDjangoPermissionsStruct:
    return UserDjangoPermissionsStruct.load(user_id)
