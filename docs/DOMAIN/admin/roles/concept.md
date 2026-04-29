# Roles — Concept

This document describes the **business concept** of a role, the rules it enforces, and how it interacts with the rest of the access system. It is the source of truth for *what* roles are and *why* they exist. For *how* they are built in code, see [models_and_control_layer_updates.md](models_and_control_layer_updates.md). For the unique design decisions made, see [decisions.md](decisions.md).

---

## 1. Definitions

### 1.1 Permission Group

A **Permission Group** is an atomic bundle of Django permissions (`auth.Permission` rows) tied to a **specific action or feature**. It answers the question: "What permissions does a person need to do **this one thing**?"

Examples:
- *Asset Lifecycle* — permissions to add, change, delete, view assets
- *Supply Management* — permissions to manage supply requests and inventory
- *Audit Report Generation* — permissions to generate and export compliance reports
- *User Administration* — permissions to add, edit, disable users and assign roles

Permission groups **do not** describe groups that people belong to. They are **not** organizational units or teams. They are **atomic capability bundles** — indivisible sets of permissions needed to complete a specific job function or feature interaction.

### 1.2 Role

A **Role** is a named relationship between **humans** and a **set of permission groups**. It represents a real-world **job profile or specialization** — the aggregated capability set and responsibilities a person holds.

Examples of roles a user might hold:
- *Technician* — base field technician role
- *Documentation Technician* — specialization of Technician; adds documentation responsibilities
- *Facilities Auditor* — audit and reporting across facilities
- *IT Manager* — IT team leadership and escalation oversight
- *Cross-site Supply Coordinator* — supply chain across multiple locations

A role bundles many permission groups together so that **assigning a role to a user means: "This user should be able to do everything this role requires."**

---

## 2. Why roles exist (and why they're different from permission groups)

Three concrete problems:

1. **Direct permission group assignment is fragile.** A real job function requires multiple permission groups (e.g., a Technician might need Asset Lifecycle, Supply Management, and Equipment Tracking groups). Assigning twenty users to five permission groups each means 100 error-prone clicks. Roles reduce that to 20 clicks.

2. **Roles tell the story of who someone is.** When an administrator views a user, seeing raw permission groups (`core.view_asset`, `core.change_supply_request`, `core.delete_equipment`) tells them *what* the user can do. Seeing roles (`Technician > Documentation Technician`, `Auditor`) tells them *who* the person is and what their **responsibilities** are. This storytelling is critical for audit, access review, and avoiding silent permission creep.

3. **Roles are stable; permissions evolve.** When a new feature ships and requires permissions, an operator updates the permission group once. Every user who holds a role that includes that group automatically gains the permission — no individual user re-assignment needed.

---

## 3. The relationship between roles and domains

**Roles and Data Domains are orthogonal systems.**

- **Roles** determine what **actions** a user can perform (`has_perm` checks).
- **Data Domains** determine what **rows** a user can see (row-level visibility filters).

A user might hold the *Technician* role (granting them action permissions) **and** the *Facility 1 Transportation* domain template (granting them visibility of those facilities' rows). Both must pass for an operation to succeed.

See [../DATA_OWNERSHIP.md](../DATA_OWNERSHIP.md) for the domain system.

---

## 4. Core rules

### Rule 1 — Multiple roles per user

A user can hold **zero or more** roles at the same time. When a user holds multiple roles, their **effective permission groups are the union of all roles' permission groups**.

Example:
```
User: Jane Doe
├─ Role: Technician (groups: Asset Lifecycle, Equipment Tracking)
└─ Role: Facilities Auditor (groups: Audit Reports, Facility Access)

Jane's effective groups: {Asset Lifecycle, Equipment Tracking, Audit Reports, Facility Access}
```

### Rule 2 — Single-layer role inheritance

Roles can form a **parent-child relationship**, but only **one level deep**. A role specializes on a parent role, extending its permission groups.

- **Base role** — has no parent. Example: *Technician*.
- **Specialized role** — has exactly one parent. Example: *Documentation Technician* (parent: *Technician*).

**Constraint:** A specialized role cannot itself be a parent. The role hierarchy is a forest of shallow trees, max depth 2.

### Rule 3 — No overlap between parent and child

A specialized role **cannot include the same permission groups as its parent**. The parent groups come automatically; the child adds *new* groups.

When a user holds a specialized role, they get:
- All permission groups from the **parent role**
- All permission groups from the **specialized role**
- But no duplicates

Example:
```
Parent: Technician
├─ groups: [Asset Lifecycle, Equipment Tracking]

Child: Documentation Technician
├─ groups: [Documentation Management, Report Generation]
├─ parent: Technician
└─ effective groups when assigned: [Asset Lifecycle, Equipment Tracking, Documentation Management, Report Generation]
```

### Rule 4 — Cascade delete on role removal

When a role is removed from the system, all roles that depend on it are also removed.

Example: If *Technician* is deleted, *Documentation Technician* (which depends on it) is also deleted. The system warns the user of all dependent roles before confirming deletion.

**Important distinction:** Removing a role from a **user** is different from deleting a role from the **system**.
- Removing a role from a user: just that role disappears from the user.
- Deleting a role from the system: triggers cascade deletion of dependent roles, affects all users who held that role.

### Rule 5 — Role relationship types

Each role assignment to a user has a **relationship** that contextualizes why they hold that role:

- **primary** — the user's main job title (e.g., "Technician").
- **specialty** — a secondary, specialized role (e.g., "Documentation Technician").
- **side_job** — occasional duties outside the main role (e.g., "Supply Coordinator").
- **for_fun** — training, temporary coverage, or learning role (not a core responsibility).

These are **labels only**, not technically enforced. They help administrators understand the user's responsibilities at a glance and guide audit decisions.

### Rule 6 — Assignment notes

Each user's role assignment has a **notes** field for free-text justification. This explains *why* the user holds their roles — especially for non-primary or unusual assignments.

Examples:
- *"Primary role — hired as field technician."*
- *"Specialty added 2026-03-15 for cross-team documentation project; sunset 2026-09-01."*
- *"Side job: supply coverage during Sarah's leave (until 2026-05-30)."*

The notes are for audit and handoff clarity, not technical enforcement.

### Rule 7 — Permission groups are never directly assigned

Permission groups are **only** assigned through roles. A user cannot hold a permission group unless it comes from a role they hold.

**Why:** This keeps the "story" clear. When an auditor asks "why does Jane have the Asset Lifecycle permission group?", the answer is always "because she holds the Technician role (which includes it)." There is no "drift" or unexplained permission state.

**Exception:** Drift detection. If a permission group is removed from a role, but a user still holds it (because another role they hold includes it, or a manual override), that is tracked as a valid state, not an error.

### Rule 8 — Roles do not grant data access

Roles manage **permission groups** (capability access). They have **zero** effect on **Data Domain** assignments (row-level access). A user with the *Technician* role still sees no rows until they have a domain template assignment or explicit `UserDomain` rows.

---

## 5. The full access picture

When a user interacts with the application, **two gates** must pass:

1. **Capability Gate** — "Does my effective permission group set (from all my roles) include the permission Django needs for this action?" (Roles feed into permission group membership; Django answers the gate.)
2. **Scope Gate** — "Does the row I'm about to touch live in a Data Domain I'm assigned to?" (Domain templates + explicit `UserDomain` assignments determine this; see [../DATA_OWNERSHIP.md](../DATA_OWNERSHIP.md).)

Roles **only** affect gate 1. They have **zero** effect on gate 2. Both gates must pass for an operation to succeed.

---

## 6. Admin guidance: reading a user's role story

When an administrator views a user's profile, they should see:

```
User: Jane Doe

Role Profile:
┌─ PRIMARY: Technician
│  ├─ groups: [Asset Lifecycle, Equipment Tracking]
│  └─ notes: Hired 2025-06-01; field technician.
│
├─ SPECIALTY: Documentation Technician
│  ├─ parent role: Technician
│  ├─ groups: [Documentation Management, Report Generation]
│  ├─ notes: Added 2026-01-15 for Q1 documentation project; sunset 2026-06-30.
│  └─ (derives parent groups automatically)
│
└─ SIDE_JOB: Supply Coordinator
   ├─ groups: [Supply Management, Inventory Tracking]
   └─ notes: Coverage during Sarah's leave; ends 2026-05-30.

Effective Permission Groups: {Asset Lifecycle, Equipment Tracking, Documentation Management, Report Generation, Supply Management, Inventory Tracking}
```

This tells a **complete story** of Jane's responsibilities. An auditor or admin can quickly understand:
- What her main job is (Technician)
- What specializations she has (documentation)
- What temporary duties she carries (supply coverage)
- Why each assignment exists (in the notes)
- What she can actually do (effective permission groups)

---

## 7. Summary

| Concern | Mechanism |
|---------|-----------|
| "What can this user do?" | Union of all permission groups from all roles they hold. |
| "Why does the user hold this role?" | Role relationship type (primary/specialty/side_job/for_fun) + assignment notes. |
| "Who holds a particular role?" | Query: User → UserRole → Role. |
| "What roles does a user hold?" | Query: User → UserRole (all active rows). |
| "If I delete this role, what breaks?" | All dependent (child) roles; system shows transitive tree before confirming. |
| "If I remove a role from a user, do they lose all permissions?" | No — only permissions **unique to that role** are removed. Permissions also in other roles stay. |
| "How are roles and domains related?" | Orthogonal. Roles grant actions; domains grant row visibility. Both required for access. |
| "Can permission groups be assigned directly?" | No — only through roles. This keeps the role story clear and prevents permission drift. |

---

## Related documents

- [decisions.md](decisions.md) — unique design decisions and their rationale.
- [examples.md](examples.md) — common role assignment scenarios.
- [../RBAC.md](../RBAC.md) — Django permission mechanics and broader access architecture.
- [../DATA_OWNERSHIP.md](../DATA_OWNERSHIP.md) — the Data Domain primitive (orthogonal system).
- [../USERS.md](../USERS.md) — user-side assignment shape and session.
- [models_and_control_layer_updates.md](models_and_control_layer_updates.md) — architectural plan for implementation.
