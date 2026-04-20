from django.contrib import admin

from app.administration.models import (
    Division,
    DivisionOrganisation,
    Organization,
    OrganizationOwnershipGroup,
    OwnershipGroup,
    UserDivision,
    UserOrganization,
    UserOwnershipGroup,
)


@admin.register(Division)
class DivisionAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "updated_at")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "division", "updated_at")
    list_filter = ("divisions",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(OwnershipGroup)
class OwnershipGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "updated_at")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(OrganizationOwnershipGroup)
class OrganizationOwnershipGroupAdmin(admin.ModelAdmin):
    list_display = ("organization", "ownership_group", "updated_at")


@admin.register(DivisionOrganisation)
class DivisionOrganisationAdmin(admin.ModelAdmin):
    list_display = ("division", "organization", "updated_at")


@admin.register(UserDivision)
class UserDivisionAdmin(admin.ModelAdmin):
    list_display = ("user", "division", "disabled", "updated_at")
    list_filter = ("disabled",)


@admin.register(UserOrganization)
class UserOrganizationAdmin(admin.ModelAdmin):
    list_display = ("user", "organization", "disabled", "updated_at")
    list_filter = ("disabled",)


@admin.register(UserOwnershipGroup)
class UserOwnershipGroupAdmin(admin.ModelAdmin):
    list_display = ("user", "ownership_group", "disabled", "updated_at")
    list_filter = ("disabled",)
