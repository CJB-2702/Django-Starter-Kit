"""Load development users, role groups, sample data ownership rows, and seeded templates."""

import os

from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from app.administration.constants import (
    GROUP_GENERIC_ADMIN,
    GROUP_GENERIC_MANAGER,
    GROUP_GENERIC_USER,
)
from app.administration.models import (
    Division,
    DivisionOrganisation,
    Domain,
    Organization,
    OrganizationDomain,
    PermissionGroupTemplate,
    PermissionGroupTemplateItem,
    UserDivision,
    UserDomain,
    UserOrganization,
    UserPermissionGroupTemplate,
)

# Two divisions → four organizations (two per division) → eight domains (two per org).
_DIVISIONS: tuple[tuple[str, str], ...] = (
    ("north", "North Division"),
    ("south", "South Division"),
)
_ORGANIZATIONS: tuple[tuple[str, str, str], ...] = (
    ("north-acme", "North Acme Ltd", "north"),
    ("north-beta", "North Beta Inc", "north"),
    ("south-acme", "South Acme Ltd", "south"),
    ("south-beta", "South Beta Inc", "south"),
)
# Suffixes for the two domains under each organization (unique slug per domain).
_DOMAIN_SUFFIXES: tuple[tuple[str, str], ...] = (
    ("site-a", "Site A"),
    ("site-b", "Site B"),
)


class Command(BaseCommand):
    help = (
        "Create generic_* users, role groups, sample division/organization/domain data, "
        "and seeded permission group templates."
    )

    def handle(self, *args, **options):
        password = os.environ.get("SEED_USER_PASSWORD", "changeme")
        super_password = os.environ.get(
            "DJANGO_SUPERUSER_PASSWORD",
            "dev-admin-password-change-me",
        )

        g_user, _ = Group.objects.get_or_create(name=GROUP_GENERIC_USER)
        g_manager, _ = Group.objects.get_or_create(name=GROUP_GENERIC_MANAGER)
        g_admin, _ = Group.objects.get_or_create(name=GROUP_GENERIC_ADMIN)

        user_ct = ContentType.objects.get(app_label="auth", model="user")
        user_perms = list(Permission.objects.filter(content_type=user_ct))
        g_admin.permissions.set(user_perms)
        manager_perm_codenames = ("view_user", "change_user", "add_user")
        g_manager.permissions.set(
            Permission.objects.filter(
                content_type=user_ct,
                codename__in=manager_perm_codenames,
            ),
        )

        def upsert_user(username, *, groups, is_staff=False):
            u, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": f"{username}@example.invalid",
                    "is_staff": is_staff,
                },
            )
            u.set_password(password)
            u.is_staff = is_staff
            u.save()
            u.groups.set(groups)
            action = "Created" if created else "Updated"
            self.stdout.write(f"{action} user {username}")
            return u

        def upsert_superuser(username):
            u, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": f"{username}@example.invalid",
                    "is_staff": True,
                    "is_superuser": True,
                },
            )
            u.set_password(super_password)
            u.is_staff = True
            u.is_superuser = True
            u.save()
            u.groups.clear()
            action = "Created" if created else "Updated"
            self.stdout.write(f"{action} superuser {username}")
            return u

        u_user = upsert_user("generic_user", groups=[g_user])
        u_mgr = upsert_user("generic_manager", groups=[g_manager], is_staff=True)
        u_adm = upsert_user("generic_admin", groups=[g_admin], is_staff=True)
        upsert_superuser("super_admin")

        divisions: dict[str, Division] = {}
        for slug, name in _DIVISIONS:
            d, _ = Division.objects.get_or_create(
                slug=slug,
                defaults={"name": name, "created_by": u_adm, "updated_by": u_adm},
            )
            divisions[slug] = d

        organizations: list[Organization] = []
        domains: list[Domain] = []

        for org_slug, org_name, div_slug in _ORGANIZATIONS:
            org, _ = Organization.objects.get_or_create(
                slug=org_slug,
                defaults={"name": org_name, "created_by": u_adm, "updated_by": u_adm},
            )
            organizations.append(org)
            DivisionOrganisation.objects.get_or_create(
                division=divisions[div_slug],
                organization=org,
                defaults={"created_by": u_adm, "updated_by": u_adm},
            )
            for d_key, d_label in _DOMAIN_SUFFIXES:
                d_slug = f"{org_slug}-{d_key}"
                d_name = f"{org_name} — {d_label}"
                domain, _ = Domain.objects.get_or_create(
                    slug=d_slug,
                    defaults={"name": d_name, "created_by": u_adm, "updated_by": u_adm},
                )
                domains.append(domain)
                OrganizationDomain.objects.get_or_create(
                    organization=org,
                    domain=domain,
                    defaults={"created_by": u_adm, "updated_by": u_adm},
                )

        north_div = divisions["north"]
        north_orgs = [o for o in organizations if o.slug.startswith("north-")]
        north_domains = [
            d
            for d in domains
            if any(d.slug.startswith(prefix) for prefix in ("north-acme-", "north-beta-"))
        ]

        def ensure_assignment(model, **lookup):
            row, created = model.all_objects.get_or_create(
                defaults={
                    "is_active": True,
                    "created_by": u_adm,
                    "updated_by": u_adm,
                },
                **lookup,
            )
            if not created and not row.is_active:
                row.is_active = True
                row.updated_by = u_adm
                row.save(update_fields=["is_active", "updated_at", "updated_by"])

        # Regional scope: North division, its orgs, and their data domains.
        for u in (u_mgr,):
            ensure_assignment(UserDivision, user=u, division=north_div)
            for org in north_orgs:
                ensure_assignment(UserOrganization, user=u, organization=org)
            for domain in north_domains:
                ensure_assignment(UserDomain, user=u, domain=domain)

        # Full sample scope across the tree.
        for u in (u_adm,):
            for div in divisions.values():
                ensure_assignment(UserDivision, user=u, division=div)
            for org in organizations:
                ensure_assignment(UserOrganization, user=u, organization=org)
            for domain in domains:
                ensure_assignment(UserDomain, user=u, domain=domain)

        # Permission group templates — three role profiles seeded for development.
        templates_seed = [
            ("basic-user", "Basic User", g_user, "Default role for read-only end users."),
            (
                "team-manager",
                "Team Manager",
                g_manager,
                "Manager role with permission grant abilities (limited to held permissions).",
            ),
            (
                "platform-admin",
                "Platform Admin",
                g_admin,
                "Full administrative profile across the platform.",
            ),
        ]
        templates_by_slug: dict[str, PermissionGroupTemplate] = {}
        for slug, name, group, description in templates_seed:
            tpl, _ = PermissionGroupTemplate.objects.get_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "description": description,
                    "is_active": True,
                    "created_by": u_adm,
                    "updated_by": u_adm,
                },
            )
            templates_by_slug[slug] = tpl
            PermissionGroupTemplateItem.objects.get_or_create(
                template=tpl,
                permission_group=group,
                defaults={"created_by": u_adm, "updated_by": u_adm},
            )

        def ensure_template(user, slug, notes):
            tpl = templates_by_slug[slug]
            UserPermissionGroupTemplate.all_objects.update_or_create(
                user=user,
                defaults={
                    "template": tpl,
                    "notes": notes,
                    "is_active": True,
                    "created_by": u_adm,
                    "updated_by": u_adm,
                },
            )

        ensure_template(u_user, "basic-user", "seed default")
        ensure_template(u_mgr, "team-manager", "seed default — North-region manager")
        ensure_template(u_adm, "platform-admin", "seed default — full platform")

        self.stdout.write(
            self.style.SUCCESS(
                "Done. Portal: generic_manager / generic_admin / generic_user "
                f"(password from SEED_USER_PASSWORD or changeme). "
                f"Django admin: super_admin (password from DJANGO_SUPERUSER_PASSWORD or default).",
            ),
        )
