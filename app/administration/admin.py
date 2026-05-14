from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from app.administration.models import (
    AllowedEmailDomain,
    User,
    Division,
    DivisionOrganisation,
    Domain,
    DomainTemplate,
    DomainTemplateItem,
    Organization,
    OrganizationDomain,
    Role,
    RoleItem,
    UserDivision,
    UserDomain,
    UserDomainTemplate,
    UserOrganization,
    UserRole,
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "slug", "is_staff", "is_active")
    readonly_fields = ("slug",)


@admin.register(AllowedEmailDomain)
class AllowedEmailDomainAdmin(admin.ModelAdmin):
    list_display = ("domain", "is_active", "created_at", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("domain",)


@admin.register(Division)
class DivisionAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "updated_at")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "division", "updated_at")
    list_filter = ("divisions",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "updated_at")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(OrganizationDomain)
class OrganizationDomainAdmin(admin.ModelAdmin):
    list_display = ("organization", "domain", "updated_at")


@admin.register(DivisionOrganisation)
class DivisionOrganisationAdmin(admin.ModelAdmin):
    list_display = ("division", "organization", "updated_at")


@admin.register(UserDivision)
class UserDivisionAdmin(admin.ModelAdmin):
    list_display = ("user", "division", "is_active", "updated_at")
    list_filter = ("is_active",)


@admin.register(UserOrganization)
class UserOrganizationAdmin(admin.ModelAdmin):
    list_display = ("user", "organization", "is_active", "updated_at")
    list_filter = ("is_active",)


@admin.register(UserDomain)
class UserDomainAdmin(admin.ModelAdmin):
    list_display = ("user", "domain", "is_active", "updated_at")
    list_filter = ("is_active",)


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "parent_role", "is_active", "updated_at")
    list_filter = ("is_active",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(RoleItem)
class RoleItemAdmin(admin.ModelAdmin):
    list_display = ("role", "permission_group", "updated_at")


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "relationship_type", "is_active", "updated_at")
    list_filter = ("is_active", "relationship_type", "role")


@admin.register(DomainTemplate)
class DomainTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "updated_at")
    list_filter = ("is_active",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(DomainTemplateItem)
class DomainTemplateItemAdmin(admin.ModelAdmin):
    list_display = ("template", "domain", "is_active", "updated_at")
    list_filter = ("is_active",)


@admin.register(UserDomainTemplate)
class UserDomainTemplateAdmin(admin.ModelAdmin):
    list_display = ("user", "template", "is_active", "updated_at")
    list_filter = ("is_active", "template")
