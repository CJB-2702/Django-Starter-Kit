# Permissions and Data Access — Summary, Questions, and Gaps

This document maps the two access control systems you are building, surfaces contradictions, asks open questions, and compares against common industry patterns. It is written at the business and conceptual level — not as implementation guidance.

---

## Two Systems, One Combined Decision

Every protected operation in this application answers two separate questions before it can proceed:

1. **System Role question:** "Is this user allowed to perform this class of action at all?"
   *Example: "Is this user allowed to edit Assets?"*

2. **Data Scope question:** "Does this specific record belong to a scope this user is allowed to see?"
   *Example: "Is this asset at Facility 2, which is one of the ownership groups assigned to this user?"*

Both questions must answer **yes** for the operation to succeed. Neither system replaces the other. The combination is the gate.

---

## System 1 — Role-Based Access Control (What You Can Do)

### How it works

| Layer | What it is | What it does |
|---|---|---|
| **Permission** | A single capability ("can change Asset") | Atomic capability tied to a model and action |
| **Permission Group** | A named bundle of permissions | Groups related permissions together (e.g. "Asset Editor") |
| **Group Template** | A named bundle of Permission Groups | Represents a real-world role spanning multiple sectors |
| **User** | A person in the system | Ends up as a member of Django groups via their assigned template |

### The template concept

A **Group Template** is your answer to the problem that a real person (e.g. an IT Technician) needs capabilities from *multiple* application sectors at once. Rather than manually assigning a dozen permission groups, you assign one template that says "this role type gets these groups across Facilities, IT, and Security."

The template is a **convenience and audit layer** — the actual permissions Django checks are still the resolved group membership, not the template itself.

### Template diff tracking

You want to record the **gap** between what a user's template says they should have and what they actually have. This is valuable for:
- Auditing drift (someone manually added or removed groups outside the template)
- Identifying when a template is out of date relative to how users are actually configured
- Knowing whether a user's access has been "customized" beyond their role profile

---

## System 2 — Data Ownership (What Records You Can See)

### How it works

```
Division
  └── Organization
        └── Ownership Group ← attached to every data record
                              also assigned to every user (many-to-many)
```

A **car record** is tagged: "this car belongs to Facility 2."
A **user** is assigned: "this user can see records for Facility 2."

The hierarchy (Division → Organization → Ownership Group) is **navigation and administration structure only.** It does not change the fundamental access check. The access check is always: **does this record's ownership group appear in the user's assigned ownership group list?**

### Overlap is intentional

Ownership groups can belong to more than one organization. A shared facility, a joint operation, or a canonical group used across organizational boundaries is modeled naturally — the ownership group is assigned to both organizations, and users from either can be assigned to it.

---

## Where the Two Systems Meet

A typical enforced query reads roughly: *"give me all assets where the asset's ownership group is in my assigned ownership groups **and** I have permission to view assets at all."*

The systems are cleanly separated:
- Role system answers capability questions ("can I do X?")
- Scope system answers data questions ("on which records?")

This separation is the right design. Keeping them separate makes each easier to reason about, audit, and debug independently.

---

## Open Questions

These are genuine ambiguities or gaps in the current design that need explicit answers before building.

### Q1: Can a user have more than one active group template?

The current documentation says "at most one group template per user." But your stated use case is an IT Technician who needs groups from the Facilities sector **and** the IT sector.

There are three possible resolutions:
- **Templates span sectors by design.** An "IT Technician" template simply includes permission groups from both Facilities and IT. Templates are cross-cutting profiles, not sector-specific ones.
- **Relax the single-template rule.** Allow multiple templates per user and merge their group sets.
- **Templates handle the common case; manual additions handle exceptions.** One template covers the primary role; additional groups can be granted individually, and the diff system tracks those additions.

Which resolution fits your real-world staffing model? This is the most important open question.

---

### Q2: What does user assignment to Division and Organization mean?

You have explicit user-to-division and user-to-organization assignments, **as well as** user-to-ownership-group assignments.

The documentation says divisions and organizations are for "navigation and administration" only — not for row-level access decisions. But if you have user→division and user→organization tables, it is easy for someone building a feature to mistakenly use those to filter records, bypassing the ownership group check.

**You need an explicit decision:** Are user→division and user→organization assignments:
1. **Purely cosmetic** (which org/division does this user "belong to" for display and admin UIs), OR
2. **Implicitly expanding ownership access** (assigning a user to an organization implies they can see all that organization's ownership groups), OR
3. **A denormalized shortcut** for bulk-assigning all ownership groups in a division or organization?

Option 2 and 3 conflict with the current design where ownership group is the atomic access primitive. If the answer is Option 1, the tables need a clear name and documentation that separates them from the access system. If Option 2 or 3, the data ownership model needs revising.

---

### Q3: What happens to a user's group memberships when their template changes?

When you assign a new template to a user (or update the template definition itself), what should happen to their existing group membership?

Common strategies:
- **Full replace:** Strip all groups derived from the old template and add those from the new template. Simple, but loses any manually-added groups.
- **Additive only:** Add new template groups; never remove. Access only grows — risky over time.
- **Rebase:** Remove template-derived groups, re-add from new template, re-apply tracked manual additions on top.
- **Snapshot-before-change:** Record a snapshot of membership before template change; surface the diff to an admin for manual review.

The diff tracking concept you described suggests you lean toward the rebase or snapshot approach. This needs to be a stated rule, not an ad-hoc implementation choice.

---

### Q4: What is a "template diff" — drift or intentional customization?

If a user has groups beyond what their template specifies, that could mean:
1. **Drift:** Someone manually added groups without updating the template — an anomaly to be corrected.
2. **Intentional customization:** This user has a unique role not fully captured by a template — the diff is the correct state.

Without a rule distinguishing these, the diff becomes noise. Consider whether you want an explicit "override reason" or approval step when groups are added outside a template, so the system knows whether deviation is intentional.

---

### Q5: As new application sectors are added, who owns the templates?

When Facilities Management, Security, and IT all generate their own permission groups, who is responsible for keeping templates current as permissions evolve? Is there a governance process — even informally — for:
- Who can create/edit a template?
- What triggers a review of existing templates when a sector adds new permissions?
- How users on "old" templates get notified or migrated?

This is a people-and-process question, not a technical one, but the system needs to support whatever answer you choose.

---

## Potential Contradictions

| Contradiction | Description |
|---|---|
| Single template vs. cross-sector roles | Documented as "at most one" but use cases imply cross-sector bundles are needed. Resolvable by making templates cross-cutting, but needs a decision. |
| User→Division/Org assignments vs. "navigation only" | Having explicit user assignment tables for Division and Organization invites misuse as access scopes when the design intent is navigation only. |
| Ownership group overlap vs. organization-based "belonging" | If User A "belongs to" San Diego but San Diego shares Facility 2 with Los Angeles, does assigning the user to San Diego org imply Facility 2 access? The model currently says "no — explicit ownership group assignment only" but this needs to be consistently enforced. |
| Template diff as audit vs. diff as correction | The diff has two possible meanings (detect drift vs. record intentional customization) and needs one of them to be primary. |

---

## Common Industry Patterns for This Type of System

What you are building is a **hybrid RBAC + ABAC** system (Role-Based Access Control + Attribute-Based Access Control). This is the standard for multi-tenant or multi-site operational software.

| Pattern | What it is | How it maps to your design |
|---|---|---|
| **RBAC** (Role-Based) | Permissions grouped into roles; users assigned roles | Your Permission → Permission Group → Template stack |
| **ABAC** (Attribute-Based) | Access decisions include record attributes (e.g. "which site is this?") | Your ownership group tagging on data rows |
| **Role Templates / Profiles** | Named bundles of roles for common staff types | Your Group Templates |
| **Effective permission set** | Resolved set of permissions after all groups merged | What Django computes from group membership; your templates feed this |
| **Scope / Tenant filter** | Secondary filter applied after capability check | Your ownership group filter on queries |
| **Drift detection** | Audit comparing expected vs. actual role assignment | Your template diff concept |

Your design is conceptually sound and aligned with how serious multi-site operational systems work. The main risk is **accidental scope expansion** — features built using Division/Organization assignments instead of Ownership Group assignments, bypassing the intended access primitive.

---

## Infrastructure Gaps — What Still Needs to Be Built

Based on current documentation and code, here is what is built versus what is described but not yet built:

| Capability | Status |
|---|---|
| Division / Organization / Ownership Group models | **Built** |
| User → Ownership Group assignments | **Built** |
| User → Division and Organization assignments | **Built** |
| Django Permission Groups (via Django built-ins) | **Built** (Django provides this) |
| **Group Template model** (named bundle) | **Not built** |
| **Group Template Items** (template ↔ Django groups linking table) | **Not built** |
| **User → Template assignment** (which template is active for this user) | **Not built** |
| **Template diff tracking** (expected groups vs. actual groups) | **Not built** |
| Enforcement layer combining RBAC + scope filter in queries | **Partially built** (control layer exists; needs consistent application as sectors grow) |

The data ownership side is structurally in place. The RBAC template side is documented but not yet built — that is your next infrastructure need if you want the template system to function.

---

## Recommended Decisions Before Building Further

1. **Decide whether a user can hold more than one group template.** This shapes the entire RBAC data model.
2. **Clarify what user→Division and user→Organization assignments are *for*.** Name them clearly and document that they are not access controls.
3. **State the rule for what happens to group membership on template change.** Pick one of: full replace, additive, rebase, or snapshot-for-review.
4. **Define when a diff is "drift" vs. "intentional customization."** Consider an approval or tagging step for out-of-template group additions.

---

*Last updated: 2026-04-23*
