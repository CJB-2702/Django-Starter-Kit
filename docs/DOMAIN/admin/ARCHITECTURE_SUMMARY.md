# Authorization & Scope System — Complete Architecture

This document summarizes the complete architecture of how **permissions** and **data scope** work together in this application, after domain templates are implemented. It serves as a validation checksum: if the system matches this description, the implementation is on track.

---

## The Two Gates

Every user action in the application faces **two independent access gates**:

### Gate 1: Permission / Capability (What You Can *Do*)

```
User
  ↓
At most one active PermissionGroupTemplate
  ↓
Resolves to auth.Group membership
  ↓
Django `has_perm()` check
  ↓
Route access + model-level action (add/change/view/delete)
```

**Data structures:**
- `PermissionGroupTemplate` — named role profile (e.g., "IT Technician")
- `PermissionGroupTemplateItem` — through-table (template ↔ auth.Group)
- `UserPermissionGroupTemplate` — assignment (user ↔ template)
- `auth.Group` — Django native; bundles `auth.Permission` rows

**Enforcement:**
- Users resolve to a single permission group template (at most).
- Assigning a template updates `user.groups` to match template's items (rebase default, additive optional).
- Drift between template and actual groups is tracked and visible but not blocking.
- Session carries resolved `user_permission_codenames` for fast checks.

---

### Gate 2: Scope / Domain (What You Can *See*)

```
User
  ↓
  UserDomain assignments (direct + template-derived)
  ↓
  Union = user's complete domain set
  ↓
  Row filter in every query
```

**Data structures:**
- `DomainTemplate` — named scope profile (e.g., "Facility 1 Transportation"); copied at assignment
- `DomainTemplateItem` — through-table (template ↔ domain); auditable with soft-delete; for audit trail only
- `UserDomainTemplate` — assignment (user ↔ template); tracks which templates have been assigned
- `UserDomain` — the single source of truth: direct assignment (user ↔ domain); may expire; may have been created by template assignment
- `Domain` — the row-level scope primitive; every scoped row has a domain FK
- `Organization`, `Division` — informational hierarchy only; do not grant access

**Enforcement:**
- Users can have zero or more active `UserDomainTemplate` assignments (templates are tools, not permissions).
- User's complete domain set = all `UserDomain` rows where `user=current_user` and `is_active=True`.
- Assigning a template **copies** all template domains to user's `UserDomain` set (rebase default, additive optional).
- Template updates propagate: new domains added to template are copied to all users with that template assigned (if not already present).
- Template item removal checks all users: domain is removed from user's set only if no other active template assigned to that user contains it.
- Drift is allowed: admins can directly assign `UserDomain` rows with no template relationship.
- Session carries resolved `user_domain_ids` for fast domain filters on every query.
- Every scoped row is visible ⟺ `row.domain_id in user_domain_ids`.

---

## Session Snapshot (Performance Critical)

At login (or after any template/domain change), the session is updated with:

```python
session['user_domain_ids'] = set(
    UserDomain.objects.filter(
        user=user,
        is_active=True,
        expires_at__isnull=True or expires_at__gt=now()
    ).values_list('domain_id', flat=True)
)

session['user_permission_codenames'] = set(
    Permission.objects.filter(
        group__user=user
    ).values_list('codename', flat=True)
)
```

**Why in the session:**
- Every data-filtered query checks `user_domain_ids` to scope rows.
- Every permission check (`has_perm`) uses Django's native `has_perm()` against `user.groups`.
- Database lookups on every request would be prohibitively slow.
- Session is updated **only** on assignment/revocation, not per-request.

**Data flow:**
- Templates are a tool; they do not appear in session.
- When a template is assigned, all its domains are copied to user's `UserDomain` rows.
- Session loads only from `UserDomain`, making the source of truth explicit.

---

## Orthogonality

The two systems are **completely independent**:

1. **Permission group template changes** do not affect domain assignments.
2. **Domain template changes** do not affect permission group membership.
3. A user can have:
   - Permission template + one or more domain templates (complete access)
   - Permission template + no domain templates (can act, but sees nothing)
   - No permission template + one or more domain templates (sees data, but can't act)
   - Neither (no access)

Both gates must pass for an operation to succeed. Neither implies the other.

The domain system is also **orthogonal to itself**: templates are tools for bulk assignment but do not gate access—only `UserDomain` rows determine visibility.

---

## Audit & History

### Permission Group Templates
- Changes to `PermissionGroupTemplate` name/description/status are tracked via audit fields (`created_by`, `updated_by`, timestamps).
- Adding/removing items from a template is tracked via `PermissionGroupTemplateItem` audit fields.
- User assignment changes (`UserPermissionGroupTemplate`) are tracked with `notes` field for justification.
- Drift (difference between template and actual groups) is visible in UI but not stored separately.

### Domain Templates
- Changes to `DomainTemplate` name/description/status are tracked via audit fields.
- **Adding/removing domains to/from a template is fully auditable:**
  - Each `DomainTemplateItem` row has audit fields (`created_by`, `updated_by`, timestamps).
  - Removed items are soft-deleted (`is_active=False`) rather than purged.
  - Historical view shows what domains a template contained at any time and who made changes.
- User assignment changes (`UserDomainTemplate`) are tracked with timestamps.
- Explicit `UserDomain` assignments are tracked with expiration and audit fields.

---

## Expiration

**Checked once at system startup** (not per-request; performance constraint):

```python
# Pseudo-code: management command
now = timezone.now()

Permission.objects.filter(expires_at__lt=now, is_active=True).update(is_active=False)
Group.objects.filter(expires_at__lt=now, is_active=True).update(is_active=False)
UserDomain.objects.filter(expires_at__lt=now, is_active=True).update(is_active=False)
UserOrganization.objects.filter(expires_at__lt=now, is_active=True).update(is_active=False)
UserDivision.objects.filter(expires_at__lt=now, is_active=True).update(is_active=False)
DomainTemplate.objects.filter(expires_at__lt=now, is_active=True).update(is_active=False)
PermissionGroupTemplate.objects.filter(expires_at__lt=now, is_active=True).update(is_active=False)
```

- Expired rows are **soft-deleted** (`is_active=False`), not removed.
- All queries filter `is_active=True` by default.
- Audit trail is complete: operators can see when/why access expired.

---

## Control-Layer Families

### Permission Granting (`control_layer/permissions/`)
- `PermissionGroupTemplateContext` — load/edit templates, add/remove items.
- `UserTemplateAssignmentContext` — assign/swap/disable permission templates.
- `TemplateRebaseHandler` — sync user's `auth.Group` membership.
- `TemplateDriftStruct` — read-only view of expected vs. actual groups.
- `TemplateAssignmentPolicy` — guard; who may assign/edit templates.

### Domain Granting (`control_layer/data_ownership/`)
- `DomainTemplateContext` — load/edit domain templates, add/remove domains (with audit; changes propagate to users).
- `UserDomainAssignmentContext` — assign/remove domain templates; manage explicit `UserDomain` assignments.
- `UserDomainSyncHandler` — when template assigned/removed, copy/remove domains from user's `UserDomain` set; update session.
- `UserDomainStruct` — read-only view of user's active domains (source of truth for access).
- `DomainAssignmentPolicy` — guard; who may assign/revoke domains + expiration rules.

---

## Constraints & Rules

### Rule 1 — Templates are tools; UserDomain is the source of truth

- Templates do **not** grant access themselves; they are assignment convenience tools.
- Only `UserDomain` rows determine what a user can see.
- When a template is assigned, all its domains are **copied** to user's `UserDomain` set.
- Admins can directly assign `UserDomain` rows with no template relationship (drift is allowed).
- Deleting a template does not delete the domains it created; user keeps those domains in their `UserDomain` set.

### Rule 2 — Multiple templates per user; synchronized assignment and removal

- Users can have **zero or more** active `UserDomainTemplate` assignments simultaneously.
- Assigning a template copies all template domains to user's `UserDomain` rows (unless already present).
- Template updates propagate: new domains added to template are copied to all users with that template assigned (if not already in their set).
- Template item removal checks all users:
  - If domain is in multiple template assignments for that user, keep it.
  - If domain is **only** in the removed template (among that user's active templates), remove it from `UserDomain`.
  - If domain was directly assigned (drift), keep it.

### Hard-coded in Policy
- **Sensitive groups cannot be self-propagated** (hardcoded list in `TemplateAssignmentPolicy`):
  - `administration_can_grant_and_remove_owned_permissions`
  - `administration_can_grant_and_remove_owned_domains`
  - `administration_can_crud_group_templates`
  - `administration_can_crud_domain_templates`
  - `system_admin`

### Soft Constraints (UI enforcement)
- One active permission template per user (enforced by DB unique index on `(user,)` where `is_active=True`).
- Admins only: create/edit templates; rebase is explicit, never silent.
- Permissions use Django's native `auth.Group` and `auth.Permission` framework.

---

## Summary Table

| Aspect | Permission System | Scope System |
|--------|-------------------|--------------|
| **Primitive** | `auth.Permission` (Django native) | `Domain` (project custom) |
| **Bundle** | `auth.Group` (Django native) | *None; domains are individual* |
| **Template** | `PermissionGroupTemplate` | `DomainTemplate` (copied at assignment) |
| **User Assignment** | `UserPermissionGroupTemplate` (one active max) | `UserDomainTemplate` (zero or more active) |
| **Source of Truth** | `auth.Group` membership (via template) | `UserDomain` rows (template-derived + drift) |
| **Session Key** | `user_permission_codenames` | `user_domain_ids` |
| **Enforcement** | Django `has_perm()` | Row filter: `row.domain_id in user_domain_ids` |
| **Audit Trail** | Template items + user assignments | Template items (soft-delete history) + assignments |
| **Drift** | Visible in UI; tracked but not blocking | Allowed; admins can directly assign `UserDomain` |
| **Expiration** | Optional on `Permission`, `Group` | Optional on `UserDomain` |
| **Template Update Propagation** | Changes do not auto-propagate to users | New domains copied to all users with template assigned |
| **Template Item Removal** | Removes from `auth.Group` per policy | Removes from `UserDomain` if no other active template contains it |

---

## Related Documents

- [RBAC.md](RBAC.md) — permission system concepts.
- [DATA_OWNERSHIP.md](DATA_OWNERSHIP.md) — domain system concepts.
- [USERS.md](USERS.md) — user model and session.
- [permission_group_templates/](permission_group_templates/) — permission template details.
- [domain_templates/](domain_templates/) — domain template details.
