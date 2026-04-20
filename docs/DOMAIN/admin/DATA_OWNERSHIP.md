# Data ownership and organizational scope (administration)

This document describes how **divisions**, **organizations**, and **ownership groups** define **record scope** for row-level access and how that scope relates to Django’s permission model. Structural definitions of core tables (foreign keys, must-have edges) are in [core/CORE_MODELS.md](../core/CORE_MODELS.md). **How users carry assignments in the database and session** is in [USERS.md](USERS.md).

---

## 1. Ownership groups as primary scope

**Ownership groups** are the primary **record scope** for row-level access and for anchoring domain data. They replace an older “location-only” mental model with an explicit hierarchy and assignment rules.

---

## 2. Hierarchy

Conceptual ordering:

**Division → Organization → Ownership Group**

- A **division** groups **organizations** (e.g. a regional or business division).
- An **organization** groups **ownership groups**—it is a *set* of ownership groups used for navigation, reporting, or administration.
- An **ownership group** is the **atomic scope** attached to data and to users (e.g. a facility, site, or other logical unit you treat as one ownership boundary).

**Overlap:** Different **organizations** may reference the **same** ownership group (shared facilities, joint operations, or re-use of a canonical group across org boundaries). The model allows that overlap by design.

**Example:** *California Regional* (division) → *San Diego* (organization) → *Facility 2* (ownership group).

---

## 3. Data rows vs. Django auth

- **Rows:** Scoped business data is expected to carry an **ownership group** (foreign key or equivalent). Treat **ownership group** as a **core dependency** across the application; see [core/CORE_MODELS.md](../core/CORE_MODELS.md).
- **Users:** Each user has **many** ownership groups assigned in the **database** (many-to-many or equivalent). Session representation and refresh rules are described in [USERS.md](USERS.md).

---

## 4. Relation to Django auth and RBAC

Ownership group membership is **not** modeled as Django `Group` / `Permission` rows per row. It is **application-level** scoping: queries, managers, services, or policy objects combine **Django permissions** (“may this user change Asset in principle?”) with **ownership group filters** (“which Asset rows match this user’s assigned groups?”). See [RBAC.md](RBAC.md) for the split between Django’s model-level gates and row rules.

---

## Related documents

- [RBAC.md](RBAC.md) — Django groups, permissions, and group templates.
- [USERS.md](USERS.md) — user assignments and session.
- [core/CORE_MODELS.md](../core/CORE_MODELS.md) — core entity table and dependency graph.
