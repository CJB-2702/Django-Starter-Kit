from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path
from app.administration.presentation_layer.entrypoints.access_management import (
    access_management_index,
    access_management_permission_detail,
    administration_permissions,
)
from app.administration.presentation_layer.entrypoints.data_ownership import (
    data_ownership_index,
)
from app.administration.presentation_layer.entrypoints.index import administration_index
from app.administration.presentation_layer.entrypoints.permission_group_portal import (
    permission_group_portal,
)
from app.administration.presentation_layer.entrypoints.scope_portals import (
    division_portal,
    organization_portal,
    ownership_group_portal,
)
from app.administration.presentation_layer.entrypoints.user_portal import (
    check_direct_permissions_against_group,
    user_portal_detail,
    user_portal_edit,
    user_portal_index,
)

urlpatterns = [
    path("", administration_index, name="administration_index"),
    path(
        "login/",
        LoginView.as_view(template_name="adm_login.html"),
        name="login",
    ),
    path(
        "logout/",
        LogoutView.as_view(),
        name="logout",
    ),
    path("user-portal/", user_portal_index, name="user_portal_index"),
    path(
        "user-portal/<int:user_id>/edit/check-direct-permissions/",
        check_direct_permissions_against_group,
        name="check_direct_permissions_against_group",
    ),
    path(
        "user-portal/<int:user_id>/edit/",
        user_portal_edit,
        name="user_portal_edit",
    ),
    path("user-portal/<int:user_id>/", user_portal_detail, name="user_portal_detail"),
    path("data-ownership/", data_ownership_index, name="data_ownership_index"),
    path("divisions/<int:division_id>/", division_portal, name="division_portal"),
    path(
        "organizations/<int:organization_id>/",
        organization_portal,
        name="organization_portal",
    ),
    path(
        "ownership-groups/<int:ownership_group_id>/",
        ownership_group_portal,
        name="ownership_group_portal",
    ),
    path(
        "access-management/permissions/<int:permission_id>/",
        access_management_permission_detail,
        name="access_management_permission_detail",
    ),
    path("access-management/", access_management_index, name="access_management_index"),
    path(
        "permission-groups/<int:group_id>/",
        permission_group_portal,
        name="permission_group_portal",
    ),
    path(
        "permissions/",
        administration_permissions,
        name="permissions_portal_index",
    ),
]
