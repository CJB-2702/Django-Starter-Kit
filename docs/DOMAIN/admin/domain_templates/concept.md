# Domain Templates — Concept

This document describes the **business concept** of a domain template, the rules it enforces, and how it interacts with row-level access control. It is the source of truth for *what* domain templates are and *why* they exist. For *how* they are built in code, see [models_and_control_layer_updates.md](models_and_control_layer_updates.md).

---

## 1. What a domain template is

A **Domain Template** is a named, pre-configured bundle of Data **domains**. It represents a real-world **data scope profile** — the domains a person in a certain role or position is expected to have access to.

Examples of scope profiles a template might represent:

- *Facility 1 Transportation* (transportation_domain + supply_domain)
- *Warehouse Operations* (warehouse_receiving + warehouse_inventory)
- *Cross-site Auditor* (all_facilities + headquarters)
- *IT Support — Field* (field_locations + it_assets)

Assigning a domain template to a user means: **"This user should have access to every domain the template bundles together."**

A domain template is **not** a permission type. It does not participate in Django's `has_perm` checks or the permission system. It is a **shortcut** for assigning related domains together and an **audit artifact** saying "this user's data scope was established via the *Facility 1 Transportation* template."

---

## 2. Why domain templates exist

Three concrete problems:

1. **Manually assigning many domains per user is error-prone.** A Warehouse Operator might belong to five domains. Onboarding twenty of them by hand means 100 opportunities to mis-assign.
2. **Domains are stable but scope evolves.** Operators need a single place to say "everyone who holds the *Facility 1 Transportation* template should now also get access to *maintenance_domain*." Update the template; future onboards and re-baselines get it automatically.
3. **Auditors need to see intent.** Looking at a user's raw `UserDomain` list does not tell you *why* they hold those domains. Seeing "User assigned: *Facility 1 Transportation* template" tells you both the scope and the business context in one glance.

---

## 3. The rules





### Rule 3 — Default assignment is REBASE

When a user's domain template changes (or is first assigned), the default behavior is:

1. Strip the domains that came from the **previous** template (if any).
2. Add every domain the **new** template references.
3. Leave everything else alone (explicit `UserDomain` assignments outside the template footprint are preserved).

This keeps template changes predictable and prevents scope creep. An **Additive** toggle is offered as an explicit opt-out when an operator wants to *layer* a new template on top of the old one.

### Rule 4 — Domain templates do not grant capabilities

Domain templates manage **data scope** (which rows you see). They have **zero** effect on **permission groups** (what actions you can perform). A user with the *Facility 1 Transportation* template still sees no rows until they have explicit `UserDomain` rows, and still cannot perform actions unless they hold the required permission groups. The two systems stay separate on purpose — see [../DATA_OWNERSHIP.md](../DATA_OWNERSHIP.md) and [../RBAC.md](../RBAC.md).

### Rule 5 — Template changes are auditable and historical

Every add/remove of a domain to/from a template is tracked:

- `DomainTemplateItem` rows are timestamped and carry audit fields (`created_by`, `updated_by`, etc.).
- When an item is removed from a template, the row is soft-deleted (`is_active=False`) rather than permanently deleted.
- Historical views show the full audit trail: what domains a template contained at any given time, who made the change, and when.

---

## 4. The full access picture

When a user interacts with the application, **two gates** must pass:

1. **Template / Data Domain gate** — "Does the row I'm about to touch live in a Domain I'm assigned to (via template or explicit assignment)?"
2. **Permission / Capability gate** — "Do I hold the required permission groups for this action?"

Domain templates **only** affect gate 1. Permission group templates (see [../permission_group_templates/concept.md](../permission_group_templates/concept.md)) **only** affect gate 2.

---

## 5. Admin warning: scope visibility

The system exposes domain template changes on the user-portal edit screen as a small panel listing:

- The user's current active template (if any).
- The domains the template bundles (grouped, labeled `[Template]`).
- Explicit `UserDomain` assignments outside the template (labeled `[Manual]`).
- An expiration countdown for explicit assignments.

Operators can **re-rebase** (sync to template), accept mixed state as-is, or swap templates. The session is updated on every change so the user's next request sees the new scope.

---

## 6. Governance (informal)

Domain template governance is a people-and-process concern rather than a code concern. The recommended (informal) practice:

- **Who creates and edits templates** — members of the `generic_admin` group.
- **When a template is reviewed** — whenever a domain is added/removed or when organizational structure changes.
- **How existing users are notified** — template changes apply **only on next assignment or explicit re-rebase**, never silently. An operator reviews who holds the template and decides which users to re-rebase.

These rules are not technically enforced but are encoded in the UI (only admins can edit templates; re-rebase is an explicit button, not automatic).

---

## 7. Summary

| Rule | Statement |
|------|-----------|
| **One per user** | At most one active template assignment per user. |
| **Reference, not copy** | Templates point at `Domain` rows; domain state is not duplicated. |
| **Rebase default** | Changing templates strips old template's domains and applies the new template's domains. Additive is opt-in. |
| **No effect on capabilities** | Templates manage data scope only; permission groups are the separate system. |
| **Changes are auditable** | Every add/remove is timestamped, soft-deleted, and visible in audit history. |
| **Distinct from permissions** | Domain templates and permission group templates are orthogonal systems. |

---

## Related documents

- [../DATA_OWNERSHIP.md](../DATA_OWNERSHIP.md) — the Data Domain primitive and the Golden Rule.
- [../RBAC.md](../RBAC.md) — permission groups and permission group templates.
- [../USERS.md](../USERS.md) — user-side assignment shape and session.
- [models_and_control_layer_updates.md](models_and_control_layer_updates.md) — architectural plan for implementation.
- [../permission_group_templates/concept.md](../permission_group_templates/concept.md) — permission group template business concept.
