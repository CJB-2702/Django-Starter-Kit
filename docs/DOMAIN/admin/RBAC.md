# Role-based access control (concepts)

This document describes **concepts** for access control in this application: what Django’s built-in authorization is used for, how **group templates** relate to Django **groups**, and where enforcement belongs relative to **row-level** rules. It is **not** a specification for UI, admin workflows, or how to build an additional administration surface.

For **who may access which rows** by ownership group and organization, see [DATA_OWNERSHIP.md](DATA_OWNERSHIP.md) and [USERS.md](USERS.md).

---

## 1. Goals

- **Route and view access:** Control who may hit which HTTP endpoints (views, APIs) using familiar Django primitives.
- **Model-level (“table”) access:** Control add/change/delete/view at the **model** (and optionally **object** in the Django sense of `ModelBackend` object permissions) using Django’s permission system—**not** for per-row business rules on arbitrary tables.
- **Operational convenience:** Allow operators to assign a **named bundle** of Django groups in one step via a **group template**, without replacing Django’s group membership as the source of truth for checks.
- **Clear boundary:** **Row-based** or **record-scoped** access (e.g. “only rows for my site”) is **outside** Django’s stock permission model; it is enforced by **application logic** (and domain models), not by stuffing row rules into `Group` / `Permission`.

---

## 2. Django built-ins in scope

### 2.1 Groups and permissions

- **`Permission`:** Tied to models (and optionally custom permissions) as defined by Django.
- **`Group`:** Named collections of `Permission` objects; **users** gain permissions by belonging to one or more groups (and optionally direct user permissions).

These are the **only** built-in mechanisms used for:

- **Endpoint / route protection:** Decorators, mixins, or middleware that consult `user.has_perm(...)`, group membership, or equivalent checks aligned with Django’s permission strings.
- **Full-model (“table”) gates:** Whether a user may perform a class of action on a **model** as a whole (e.g. “can add Asset”, “can change Ownership Group”).

### 2.2 What Django authorization is **not** used for

- **Row-level access control** on arbitrary tables: e.g. “see only assets in ownership groups I belong to” or “edit only records scoped to my assigned ownership groups.”
- **Dynamic scoping** that varies per row based on business attributes: that belongs in **queries, managers, services, or policy objects** that apply filters and rules using domain data—not `Permission` rows per row.

Stated plainly: **Django groups and permissions gate routes and coarse model capabilities; they do not encode row-level rules.**

---

## 3. Group templates (abstraction layer)

A **group template** is an **additional** abstraction **above** Django’s `Group`. It does **not** replace Django groups; it **references** them.

### 3.1 Purpose

- Give a **single named profile** (e.g. “Inventory clerk – Site A”) that corresponds to **multiple** Django groups at once.
- Avoid manually assigning many groups when the product’s roles are stable bundles of Django permissions.

### 3.2 Conceptual data (two logical tables)

| Concept | Role |
|--------|------|
| **`group_templates`** | Holds **template identity**: a human-readable **name**, metadata (description, audit fields, active flag, etc.—**conceptual only** here). |
| **`group_template_items`** | **Rows** linking a `group_template` identifier to **many** Django **`Group`** rows (`ForeignKey` to `auth.Group` or equivalent). |

Each **item** says: “this template includes **this** Django group.” A template may reference **many** groups; a group may appear in **many** templates.

### 3.3 Assignment semantics

When a **user** is **assigned a group template**:

- The system ensures the user is a member of **every** Django group listed in **`group_template_items`** for that template (idempotent add to group membership).
- Removing or changing template assignment is a **product decision** (e.g. remove groups that came only from that template); this document only states the **intended** effect: **template ⇒ union of referenced groups**.

Effective permissions remain **Django’s**: `User` ↔ `Group` ↔ `Permission`. The template is a **convenience and documentation** layer, not a parallel permission engine.

### 3.4 One stored template per user

The product **stores at most one** **group template identifier** per user (the “active” or “selected” template for this mechanism, if that is how assignment is modeled). Details of that field and user lifecycle live in [USERS.md](USERS.md).

---

## 4. Layered picture (conceptual)

```
Row-level rules (queries, domain policy)
        ↑ not Django Permission
Django Permission / Group (routes + model-level actions)
        ↑
Group template (optional bundle of Django groups)
        ↑
User
```

- **Bottom:** User may be linked to **one** group template id (conceptual); see [USERS.md](USERS.md).
- **Middle:** Django **groups** and **permissions** answer “may this user perform this action on this **model**” and “may this user access this **view**.”
- **Top:** **Row** and **tenant** rules use **application data** and explicit filters—not Django’s group/permission tables for per-row decisions. See [DATA_OWNERSHIP.md](DATA_OWNERSHIP.md).

---

## 5. Summary rules

| Concern | Mechanism |
|--------|-----------|
| Web routes / endpoints | Django auth + `Permission` / `Group` (or equivalent checks) |
| Model-wide (table) capabilities | Django `Permission` on models; groups aggregate permissions |
| Bundling several Django groups for one user | **Group template** + **group_template_items** → sync user into referenced groups |
| User’s template reference | **At most one** `group_template` id stored per user (conceptual); see [USERS.md](USERS.md) |
| Per-row / scoped data access | **Application-level** enforcement; **not** Django groups/permissions for row rules |
| Ownership group scope (divisions, organizations, row FKs, user assignments) | Domain models + session-backed membership; see [DATA_OWNERSHIP.md](DATA_OWNERSHIP.md) and [core/CORE_MODELS.md](../core/CORE_MODELS.md) |

---

## 6. Out of scope for this document

- Screens, workflows, or APIs for managing templates or assignments.
- Migration strategy, exact schema, or naming of fields on `group_templates` beyond the concepts above.
- Choice of `django-guardian` or other object-permission packages; this document assumes **stock** `auth` unless the project adopts something else in a separate decision.

---

## Related documents

- [README.md](README.md) — administration documentation index.
- [STANDARDS.md](../ARCHITECTURE/STANDARDS.md) — project principles and documentation index.
- [DATA_OWNERSHIP.md](DATA_OWNERSHIP.md) — organizational hierarchy and row-level scope.
- [USERS.md](USERS.md) — user model and ownership assignment.
- [core/CORE_MODELS.md](../core/CORE_MODELS.md) — core entities and FK rules.
