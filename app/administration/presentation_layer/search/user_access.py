"""Loaders for user permission and ownership aggregates."""

from app.administration.control_layer.data_ownership.user_data_ownership_struct import (
    UserDataOwnershipStruct,
)
from app.administration.control_layer.permissions.user_django_permissions_struct import (
    UserDjangoPermissionsStruct,
)


def load_user_data_ownership_struct(user_id: int, *, eager: bool = True) -> UserDataOwnershipStruct:
    return UserDataOwnershipStruct.load(user_id, eager=eager)


def load_user_django_permissions_struct(user_id: int) -> UserDjangoPermissionsStruct:
    return UserDjangoPermissionsStruct.load(user_id)
