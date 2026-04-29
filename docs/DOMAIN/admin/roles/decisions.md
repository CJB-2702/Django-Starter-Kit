# Roles — Design Decisions

This document outlines the **unique design decisions** made in this role system and explains **why** they were chosen. It complements [concept.md](concept.md), which describes *what* roles are. This document addresses the *why* — the trade-offs and reasoning behind constraints that aren't obvious from reading the concept alone.

---

## Decision 1: Multiple roles per user (union model)

**Decision:** A user can hold **zero or more roles simultaneously**, and their effective permission groups are the **union** of all roles.

**Why this, not alternatives:**

| Alternative | Trade-off |
|---|---|
| **Single role per user** (old model) | Cleaner constraint, but requires mega-templates like "IT Technician + Facilities Auditor in One". Real people have multiple jobs; bundling them into one role obscures individual responsibilities. Audit becomes "this user does everything this role says" — which is not precise. |
| **Role stacking with conflict resolution** | Complex. What if two roles conflict (one grants X, the other denies it)? Django's permission system doesn't support denials; conflicts require explicit policy. Union is simpler and reflects reality: people accumulate responsibilities. |

**Rationale:** Real people hold multiple jobs. A Technician might also be an Auditor. Jane might be "Technician + Documentation Specialist + Supply Coordinator" — each a distinct responsibility, each with its own permission set. Union semantics mean her effective permissions are "everything she needs for all three jobs." This is intuitive and audit-clear.

---

## Decision 2: Single-layer role inheritance (max depth 2)

**Decision:** A role can depend on another role, but only **one level deep**. Base roles have no dependencies; specialized roles depend on a base. Specialized roles cannot be parents.

```
Allowed:
  Technician (base)
  └─ DocumentationTechnician (specialized, parent: Technician)

Not allowed:
  Technician (base)
  └─ DocumentationTechnician (specialized)
     └─ DocumentationTechnicianTrainer (would be depth 3)

  Auditor (base)
  └─ ComplianceAuditor (specialized)
     └─ ComplianceAuditorManager (would be depth 3)
```

**Why this, not alternatives:**

| Alternative | Trade-off |
|---|---|
| **No inheritance at all** | Simpler schema, but all roles are flat peers. If DocumentationTechnician needs everything Technician has, you either duplicate those permission groups (maintenance nightmare) or manually maintain the relationship in docs. No automatic connection. |
| **Arbitrary DAG (deep nesting)** | Fully flexible, but introduces complexity. Cascade delete becomes a graph traversal. Admins can create hard-to-reason-about hierarchies (A→B→C→D→E). Validation is harder (cycle detection, depth limits, etc.). Most real org structures don't go past 2 levels anyway. |

**Rationale:** Real specializations are shallow. A Technician can specialize to "Documentation Technician" or "Hardware Specialist." Those specialists rarely specialize further. One level of inheritance captures 95% of use cases. The constraint makes validation trivial, cascade delete predictable, and the role tree easy to visualize and explain to admins.

A role can be rebased as needed. a manager has all the permissions of a technician but if more specialization is needed it likely indicates its a new base role and should be made independent

---

## Decision 3: No permission group overlap between parent and child

**Decision:** A specialized role **cannot include the same permission groups as its parent**. Child roles **extend** the parent; they do not duplicate.

**Why this, not alternatives:**

| Alternative | Trade-off |
|---|---|
| **Allow overlap** | Simpler to define roles (no validation). But when a child role is created, there's no clear semantics: does the child replace the parent, supplement it, or override it? Overlap creates confusion. Is `DocumentationTechnician` a "technician who also does docs" or a "different kind of technician"? The fact that they share groups makes it ambiguous. Also, overlap increases the chance of silent permission creep: "we added a group to both roles; did anyone notice?" |
| **Unrelated roles can overlap (but not parent-child)** | Good compromise. Allow `SupplyTechnician` and `SupplyManager` (unrelated) to both include "Supply Management" groups. But require `DocumentationTechnician` and its parent `Technician` to split. This keeps specialization hierarchies clean while allowing multiple independent roles to have real overlap. |

**Rationale:** Inheritance should mean "add on top of," not "duplicate." Enforcing no-overlap makes the relationship explicit: parent is the foundation, child adds. When an admin sees `DocumentationTechnician` depends on `Technician`, they immediately understand "you get Technician's groups plus the doc groups." Forbidding overlap prevents the ambiguity of "does this user get the permission group once or twice?" and reduces the chance of accidental duplication during schema evolution.

**Implementation note:** Validation on role creation/update checks: if this role has a parent, none of its permission groups can be in the parent's group set. This is a cheap O(N) check.

---

## Decision 4: Cascade delete on role dependency

**Decision:** When a base role is deleted from the system, all specialized roles that depend on it are **automatically deleted**. The system shows the user a transitive tree of all dependent roles **before** confirming deletion.

**Why this, not alternatives:**

| Alternative | Trade-off |
|---|---|
| **Soft constraint (warn but allow)** | Less destructive upfront, but leaves orphaned roles in the system. Admins later encounter roles with missing parents and don't understand them. Or the system must handle "roles with missing parents" as a special case. Complexity. |
| **Reassign children to a different parent** | More permissive, but confusing. If I delete Technician and reassign DocumentationTechnician to Manager, the semantics break: "DocumentationManager"? Doesn't make sense. |

**Rationale:** A specialized role **only makes sense in the context of its parent**. DocumentationTechnician is meaningless without Technician — the name says so. Deleting the parent means the specialization no longer applies. Cascade delete is the natural action. **However**, the UI must show the full tree of affected roles **before** confirming, so admins see exactly what they're deleting. This is transparent destruction, not silent.

---

## Decision 5: Cascade is directional (remove parent, not child)

**Decision:** When a user has a specialized role and its parent is removed from their role list, the child is **also removed**. When a user has only the child role and it is removed, the parent **stays** (though the user will lack the foundation that makes the child meaningful).

**Why:**

This follows from the inheritance model: a child depends on its parent. If the parent is gone, the child is a dangling specialization. However:

- **Remove child, keep parent:** Sensible. The user is still a Technician; just not a Documentation Technician anymore.
- **Remove parent, must remove child:** Required. The user is no longer a Technician; being a Documentation Technician alone violates the inheritance contract.

**Implementation:** When removing a role from a user:
1. Check if the role being removed is a parent.
2. If yes, also remove all its children from that user.
3. If no (the role is a base or child), just remove it.

---

## Decision 6: Role relationship types (primary, specialty, side_job, for_fun)

**Decision:** Each role assignment to a user carries a **relationship type** enum: `primary`, `specialty`, `side_job`, `for_fun`.

**Why this, not alternatives:**

| Alternative | Trade-off |
|---|---|
| **No relationship types** | Simpler data model. But all roles look equal in the UI. An admin can't quickly tell "this user's main job is Technician and they have a side supply role." The role story becomes muddier. |
| **One role designated as "primary"** | Also works, but requires a unique constraint (only one primary per user). What if a user has two co-equal jobs? Reduces expressiveness. |

**Rationale:** The goal is storytelling. An admin should look at Jane's roles and immediately understand her **primary responsibility**, her **specializations**, and her **temporary/side duties**. The relationship type is a one-word label that conveys this. It's not enforced (no unique constraint), so a user can have multiple primaries if needed (rare but realistic). It's purely informational, but it guides audit and access review.

---

## Decision 7: Assignment notes are per-assignment, not per-role

**Decision:** Each `UserRole` assignment has a **notes** field explaining why *this user* has *this role*. The role definition itself has a separate description field (explaining what the role is, not why a specific person was assigned it).

**Why this, not alternatives:**

| Alternative | Trade-off |
|---|---|
| **Notes only on role definition** | Role notes can explain "what is a Documentation Technician?" but not "why does Jane have it?" An admin assigning Jane to the role has no place to record "temporarily added for Q2 documentation project; review in June." |
| **Notes only on assignment** | Loses the *role* context. When an admin reviews the role definition, they can't see any guidance about *when* to assign it. |

**Rationale:** Both are useful. Role description explains the role; assignment notes explain the user's assignment. Assignment notes are how auditors later understand "is this access still needed?" and "when should we review this?"

---

## Decision 8: Permission groups are only assigned through roles, never directly

**Decision:** A user **cannot** hold a permission group directly. All permission groups must come through a role assignment. There is no separate `UserPermissionGroup` table or direct grant.

**Why this, not alternatives:**

| Alternative | Trade-off |
|---|---|
| **Allow direct permission group grants** | More flexible, but breaks the role-story principle. A user could hold permission groups from roles AND direct grants. Auditor asks "why does this user have the Asset Lifecycle group?" and the answer is "...we're not sure, it might be from a role or might be a direct grant." The story breaks. |

**Rationale:** Keeping the story intact requires that all permissions flow through roles. If an admin needs to grant an extra permission, they should either:
1. Create or extend a role.
2. Assign a second role.
3. Explicitly document it in the assignment notes.

This forces clarity: every permission group on a user is traceable to a specific role assignment and has a documented reason. No orphaned permissions. No mystery grants.

---

## Decision 9: Roles are orthogonal to Data Domains

**Decision:** A role has **zero** effect on a user's data scope (which rows they see). Data scope is managed entirely by the domain system.

**Why:**

Mixing role and domain would mean "what you can see depends on who you are and what you're allowed to do." This is tempting but wrong:

- A Technician might need to see assets in Facility A and not Facility B, independent of being a Technician. The domain is the right place for that boundary.
- A Technician and an Auditor might both need to see the same facility's assets (one to fix them, one to review compliance), but have different permission groups for actions.

Keeping them separate means: roles answer "what can you do?", domains answer "what can you see?" Both are required; neither is derived from the other.

---

## Decision 10: Validation: reject cycles at role-definition time

**Decision:** The system rejects any role dependency that would create a cycle (e.g., A depends on B and B depends on A). Cycle detection happens **at save time** when creating/updating role dependencies.

**Why now, not later:**

Detecting cycles at schema time (when the dependency is created) is better than runtime (when the user is assigned):
- **Schema time:** Cheap check, prevents invalid state from ever existing, simple error message.
- **Runtime:** Expensive traversal every time a user is assigned, and error happens after the admin has already tried to assign.

**Implementation:** When creating a `RoleDependency(child → parent)`, check:
1. `parent` has no outgoing dependencies (would violate single-layer rule).
2. `child` has no incoming dependencies (would make child a parent).
3. No role currently depends on `child` (would create a potential cycle in a future edge).

All three checks ensure the forest structure is maintained.

---

## Decision 11: No multi-parent roles

**Decision:** A role can have **at most one parent**. A role cannot depend on multiple roles.

**Why this, not alternatives:**

| Alternative | Trade-off |
|---|---|
| **Allow multi-parent (multiple inheritance)** | More flexible, but complex. Which parent's groups take precedence? What if parents conflict? Role trees become DAGs, cycle detection is harder. Most real specializations have one clear parent anyway. |

**Rationale:** The max-depth-2 forest structure is easier to reason about, validate, and visualize. A Technician has one parent (none — it's a base). A DocumentationTechnician has one parent (Technician). Clean, simple, sufficient.

---

## Decision 12: Union resolution (not intersection or override)

**Decision:** When a user holds multiple roles, their effective permission groups are the **union**. No role "overrides" another; no intersection logic.

**Why:**

- **Union:** User gets everything from all roles. Intuitive — "I'm a Tech AND an Auditor means I can do Tech things AND Audit things."
- **Intersection:** User gets only permissions in *all* roles. Confusing and rarely useful — "I can only do things all my roles allow" doesn't match mental models.
- **Override:** Which role wins? Creates implicit precedence and complexity.

Union is the simplest and most intuitive.

---

## Summary: The why behind the system

This system was designed with three principles:

1. **Clarity.** Every permission on a user should trace back to a role assignment with a documented reason. No mystery permissions.
2. **Simplicity.** Single-layer inheritance, union semantics, and no multi-parent keep the system easy to reason about and implement.
3. **Storytelling.** Looking at a user's roles should tell you who they are, what they're responsible for, and why. This drives better audit, access review, and maintenance.

---

## Related documents

- [concept.md](concept.md) — what roles are and how they work.
- [examples.md](examples.md) — real scenarios illustrating these decisions.
