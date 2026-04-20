# Users and administration (concepts)

This document describes how **users** participate in **administration**: dependency of audited models on a **user** table, **group template** metadata stored per user, **Django group membership**, and **ownership group** assignments used for row-level scope. For Django permission mechanics and group templates, see [RBAC.md](RBAC.md). For the organizational hierarchy around ownership groups, see [DATA_OWNERSHIP.md](DATA_OWNERSHIP.md).

---

## 1. Auditing and the user table

Core and downstream apps use **auditable** models (creator, timestamps, last updater). That pattern assumes a shared **user** model (or compatible FK target) for those references. See [core/CORE_MODELS.md](../core/CORE_MODELS.md) for which domain models are auditable.

---

## 2. Group template reference on the user

The product **stores at most one** **group template identifier** per user when using the template mechanism (see [RBAC.md](RBAC.md), section 3).

- That field is **metadata** about **which template** was used or is current; **authorization checks** still rely on **resolved group membership** and `Permission` as Django defines.
- If the user’s template changes, group membership is updated to match the new template’s bundle (per product rules).

---

## 3. Ownership group assignments

- **Database:** Users have **many** ownership groups (many-to-many or equivalent). This is the **source of truth** for which scopes apply to a user.
- **Session:** While interacting with the application, that assignment (or a derived “active” subset, depending on product rules) is **represented in the session** so list views, APIs, and policy checks can enforce scope **without** re-resolving full membership from the database on every request. Exact session shape and refresh rules are implementation details.

Combining **Django permissions** with **ownership group filters** is the standard pattern for “may this user do this action on **these** rows?”—not Django `Permission` per row.

---

## Related documents

- [RBAC.md](RBAC.md) — group templates and Django permission boundaries.
- [DATA_OWNERSHIP.md](DATA_OWNERSHIP.md) — division, organization, and ownership group scope.
- [core/CORE_MODELS.md](../core/CORE_MODELS.md) — core entities and auditing expectations.
