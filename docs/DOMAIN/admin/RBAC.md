# Role-based access control (concepts)

This document describes **concepts** for capability access control in this application: what Django's built-in authorization covers, how **roles** (bundles of permission groups) relate to Django `Group` rows, and where enforcement belongs relative to **row-level** (domain) rules. For **row-level** data scoping, see [DATA_OWNERSHIP.md](DATA_OWNERSHIP.md).

**See [roles/](roles/) for the authoritative role system documentation.** This page provides the broader context; [roles/concept.md](roles/concept.md) explains roles in detail.

---

## 1. Terminology

| Term | Django-level concept | What it means here |
|------|----------------------|--------------------|
| **Permission** | `auth.Permission` | A single capability, tied to a model and action (e.g. `core.change_asset`). |
| **Permission group** | `auth.Group` | An atomic bundle of permissions tied to a **specific action or feature** (e.g., "Asset Lifecycle" = permissions to add/change/delete/view assets). **Not** a social/organizational group. Permission groups are assigned to users **only through roles**. |
| **Role** | *this project* | A named relationship between humans and a set of permission groups. Represents a real-world job profile or specialization. Users can hold multiple roles; their effective permissions are the union of all roles. See [roles/concept.md](roles/concept.md). |
| **Data domain** | *this project* | Row-level access scope — separate system. See [DATA_OWNERSHIP.md](DATA_OWNERSHIP.md). |

---

## 2. Goals

- **Route and view access** — Control who may hit which HTTP endpoints using Django's `has_perm`, group membership, or equivalent checks.
- **Model-level (table) gates** — Control `add/change/delete/view` at the **model** level via `Permission`.
- **Operational convenience** — Assign a **role** in one step so a user gets all the permission groups that match their job profile. Multiple roles can be assigned.
- **Clear storytelling** — A user's roles tell an audit-friendly story of who they are and what they're responsible for.
- **Clear boundary with row-level rules** — Row-level scoping is **domain-based** (see [DATA_OWNERSHIP.md](DATA_OWNERSHIP.md)), not expressed through `Permission` rows per row.

---

## 3. Django built-ins — scope

### 3.1 Permission and Permission Group

- **`Permission`** — tied to models (and custom permissions).
- **Permission Group (`auth.Group`)** — named collections of `Permission`. Users gain permissions by belonging to one or more permission groups (and optionally direct user permissions).

These are the **only** built-in mechanisms used for:

- **Endpoint / route protection** — decorators, mixins, or middleware that consult `user.has_perm(...)` or group membership.
- **Full-model (table) gates** — whether a user may perform a class of action on a **model** (e.g. "can add Asset").

### 3.2 What Django authorization is NOT used for

- **Row-level access** — for example "see only assets in domains I belong to." That is the **domain** filter, applied at query time (see [DATA_OWNERSHIP.md](DATA_OWNERSHIP.md)).
- **Dynamic scoping** — per-row rules based on business attributes belong in **managers, services, or policy objects**, not in `Permission` rows.

---

## 4. Roles

A **Role** is a named relationship between a user and a set of permission groups. It represents a real-world job profile (e.g., *Technician*, *Documentation Technician*, *Auditor*). Users can hold **multiple roles**; their effective permission groups are the **union** of all roles they hold.

**Key properties:**
- A user can hold zero or more roles.
- Permission groups are **only** assigned through roles (never directly).
- Roles can form a parent-child relationship for specialization (e.g., *DocumentationTechnician* specializes *Technician*), but only **one level deep**.
- No permission group overlap between a parent role and its child role.
- Removing a parent role cascades the deletion of dependent child roles.
- Each role assignment includes notes explaining why the user holds it.

**For full details, see [roles/concept.md](roles/concept.md), [roles/decisions.md](roles/decisions.md), and [roles/examples.md](roles/examples.md).**

---

## 5. Roles and Data Domains are orthogonal

This application has **two independent systems** that work in parallel:

- **Roles** — bundles of permission groups (what you can *do*). Affects Django `has_perm` checks and route access.
- **Domain Templates + UserDomain** — bundles of domains (what you can *see*). Affects row-level visibility filters.

Neither system affects the other. A user might be assigned the *"Technician"* role (granting specific capabilities) and the *"Facility 1 Transportation"* domain template (granting access to specific rows). Both are required; neither is derived from the other.

---

## 6. Layered picture (conceptual)

```
Row-level scope (Domain Template + explicit UserDomain assignments)
        ↑
Django Permission / Permission Group (routes + model-level actions)
        ↑
Role (zero or more per user; union of permission groups)
        ↑
User
```

Additionally:

```
Domain Template (optional bundle of domains)
        ↑
UserDomain (explicit scope assignment)
        ↑
User
```

- **Capability layer:** user holds zero or more roles; each role resolves to `auth.Group` membership; union of all roles drives `has_perm` checks.
- **Scope layer:** user holds zero or more domain template + explicit `UserDomain` assignments; union of these resolves to domain set; drives row filters.
- **Bottom:** user is the anchor for both systems.

---

## 7. Summary rules

| Concern | Mechanism |
|---|---|
| Web routes / endpoints | Django auth + permission group membership / `has_perm` |
| Model-wide (table) capabilities | Django `Permission` on models; permission groups aggregate permissions |
| Bundling permission groups for a user | Roles + items → permission group membership (union across all active roles) |
| User's role assignment | Zero or more `UserRole` rows; each includes notes explaining why |
| Permission groups directly assigned | Not allowed; all groups come through roles |
| Role inheritance | Single-layer only: base roles (no parent) and specialized roles (one parent) |
| Cascade delete | Removing a parent role removes all child roles depending on it |
| Bundling domains for a user | Domain template + items → domain assignments |
| User's domain template reference | Exactly one `UserDomainTemplate` row per user (active assignment) |
| Per-row / scoped data access | **Domain** membership (via template or explicit `UserDomain`); see [DATA_OWNERSHIP.md](DATA_OWNERSHIP.md) |
| Two independent systems | Roles (what you can do) + domains (what you can see) are orthogonal |

---

## 8. Out of scope here

- Schema or field lists for roles — see [roles/models_and_control_layer_updates.md](roles/models_and_control_layer_updates.md).
- Role concepts and decisions — see [roles/concept.md](roles/concept.md) and [roles/decisions.md](roles/decisions.md).
- Screen layouts, portal flows — see user-portal templates.
- Object-permission packages like `django-guardian` — not in use; stock `auth` only.

---

## Related documents

- [README.md](README.md) — administration documentation index.
- [roles/concept.md](roles/concept.md) — role business concept, rules, and the full access picture.
- [roles/decisions.md](roles/decisions.md) — design decisions and rationale.
- [roles/examples.md](roles/examples.md) — common role assignment scenarios.
- [DATA_OWNERSHIP.md](DATA_OWNERSHIP.md) — the Data Domain primitive and the Golden Rule.
- [USERS.md](USERS.md) — user model, domain assignments, session.
- [domain_templates/concept.md](domain_templates/concept.md) — domain template business concept.
- [domain_templates/models_and_control_layer_updates.md](domain_templates/models_and_control_layer_updates.md) — domain template implementation plan.
- [core/CORE_MODELS.md](../core/CORE_MODELS.md) — core entity table and dependency graph.
