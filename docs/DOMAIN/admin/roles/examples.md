# Roles — Examples

This document walks through common role assignment scenarios to illustrate how the role system works in practice.

---

## Scenario 1: Simple base role

**Situation:** Onboarding a new field technician.

**Assignment:**
```
User: Alex Chen
├─ Role: Technician (primary)
│  └─ Permission groups: [Asset Lifecycle, Equipment Tracking, Field Work]
│  └─ Notes: "Hired 2026-04-01 as field technician."
│
Effective permission groups: {Asset Lifecycle, Equipment Tracking, Field Work}
Data scope: (separate; assigned via domain template)
```

**What Alex can do:**
- View, add, change, delete assets (from Asset Lifecycle group)
- Track equipment status (from Equipment Tracking group)
- Record field work (from Field Work group)

**What Alex cannot do:**
- View compliance audit reports (not in Technician role)
- Generate system reports (not in Technician role)
- Manage users (not in Technician role)

---

## Scenario 2: Multiple independent roles (union)

**Situation:** A technician who is also an auditor (two separate jobs).

**Assignment:**
```
User: Blake Moore
├─ Role: Technician (primary)
│  └─ Permission groups: [Asset Lifecycle, Equipment Tracking, Field Work]
│  └─ Notes: "Primary role; hired as technician."
│
├─ Role: Facilities Auditor (specialty)
│  └─ Permission groups: [Audit Reports, Facility Access, Compliance Review]
│  └─ Notes: "Added 2026-01-15; cross-functional audit project."
│
Effective permission groups: {Asset Lifecycle, Equipment Tracking, Field Work, Audit Reports, Facility Access, Compliance Review}
```

**What Blake can do:**
- Everything a Technician can do (Asset Lifecycle, Equipment Tracking, Field Work)
- **Plus** everything an Auditor can do (Audit Reports, Facility Access, Compliance Review)

**Query:** Union of both roles' permission groups. No overlap (unrelated roles can share groups if they need to, but these don't).

**Key point:** Blake holds two **independent, equal responsibilities**. The roles don't interact — it's just "Blake has this role AND that role."

---

## Scenario 3: Specialized role (inheritance)

**Situation:** A technician who specializes in documentation.

**Assignment:**
```
User: Casey Rodriguez
├─ Role: Technician (primary)
│  └─ Permission groups: [Asset Lifecycle, Equipment Tracking, Field Work]
│  └─ Notes: "Primary role; field technician."
│
├─ Role: Documentation Technician (specialty)
│  └─ Parent: Technician
│  └─ Permission groups: [Documentation Management, Report Generation]
│  └─ Notes: "Specialized role added 2026-02-01 for Q1 documentation project; sunset 2026-06-30."
│
Effective permission groups: {Asset Lifecycle, Equipment Tracking, Field Work, Documentation Management, Report Generation}
```

**Key point:** `DocumentationTechnician` **depends on** `Technician`. When Casey is assigned `DocumentationTechnician`:
1. If Casey is not already a `Technician`, the system auto-adds the `Technician` role.
2. Casey's effective groups are: Technician's groups + DocumentationTechnician's groups.
3. There is **no overlap** — DocumentationTechnician does not include Asset Lifecycle, Equipment Tracking, or Field Work (those come from Technician).

**What Casey can do:**
- Everything a Technician can do.
- **Plus** write and generate documentation (Documentation Management, Report Generation).

**Removing the role:**
- If Casey's `Documentation Technician` role is removed, they **keep** the `Technician` role. They can still do field work.
- If Casey's `Technician` role is removed, the system **also removes** `Documentation Technician` (it becomes orphaned). The warning shows: "Removing Technician will also remove: Documentation Technician. Confirm?"

---

## Scenario 4: Specialization hierarchy with multiple children

**Situation:** An organization with a core Technician role and several specializations.

**Role structure:**
```
Technician (base)
├─ Documentation Technician
├─ Hardware Specialist
└─ Safety Inspector
```

**Assignments:**
```
User: Dana Kim
├─ Role: Technician (primary)
│  └─ Permission groups: [Asset Lifecycle, Equipment Tracking, Field Work]
│
├─ Role: Hardware Specialist (specialty)
│  └─ Parent: Technician
│  └─ Permission groups: [Hardware Configuration, Diagnostics]

User: Elena Patel
├─ Role: Technician (primary)
│  └─ Permission groups: [Asset Lifecycle, Equipment Tracking, Field Work]
│
├─ Role: Safety Inspector (specialty)
│  └─ Parent: Technician
│  └─ Permission groups: [Safety Compliance, Incident Reporting]
```

**Key point:** The same base role (Technician) can have multiple specializations. Different users can specialize along different branches. If Technician is deleted, **both** Hardware Specialist and Safety Inspector are cascade-deleted.

---

## Scenario 5: Multiple roles, including specializations

**Situation:** A person with multiple job functions, one of which is specialized.

**Assignment:**
```
User: Frank Lopez
├─ Role: Technician (primary)
│  └─ Permission groups: [Asset Lifecycle, Equipment Tracking, Field Work]
│  └─ Notes: "Primary role; field technician."
│
├─ Role: Documentation Technician (specialty)
│  └─ Parent: Technician
│  └─ Permission groups: [Documentation Management, Report Generation]
│  └─ Notes: "Specialization added 2026-03-01 for documentation project; review 2026-06-01."
│
├─ Role: Supply Coordinator (side_job)
│  └─ Permission groups: [Supply Management, Inventory Tracking]
│  └─ Notes: "Temporary role; covering for Sarah during leave (until 2026-05-30)."
│
Effective permission groups: {Asset Lifecycle, Equipment Tracking, Field Work, Documentation Management, Report Generation, Supply Management, Inventory Tracking}
```

**Audit trail (from the admin UI):**
```
PRIMARY: Technician
  ├─ Asset Lifecycle, Equipment Tracking, Field Work
  └─ Hired 2026-01-01 as field technician.

SPECIALTY: Documentation Technician
  ├─ (derives from parent Technician: Asset Lifecycle, Equipment Tracking, Field Work)
  ├─ Documentation Management, Report Generation
  └─ Assigned 2026-03-01; project sunset 2026-06-01.

SIDE_JOB: Supply Coordinator
  ├─ Supply Management, Inventory Tracking
  └─ Covering Sarah's leave (until 2026-05-30).
```

**Story:** Frank is a technician (primary), with specialization in documentation (specialty), and temporarily covering supply duties (side job). His effective permissions are the union of all three roles. When the supply coverage ends, the admin removes Supply Coordinator; Frank's primary and specialty roles remain.

---

## Scenario 6: Overlapping permission groups across unrelated roles

**Situation:** Two roles that both need the same permission groups (not parent-child).

**Role structure:**
```
SupplyTechnician (base)
├─ Permission groups: [Supply Management, Asset Lifecycle]

SupplyManager (base, unrelated)
├─ Permission groups: [Supply Management, Management, Reporting]
```

**Assignment:**
```
User: Grace Thompson
├─ Role: SupplyTechnician (primary)
│  └─ Permission groups: [Supply Management, Asset Lifecycle]
│
├─ Role: SupplyManager (specialty)
│  └─ Permission groups: [Supply Management, Management, Reporting]
│
Effective permission groups: {Supply Management, Asset Lifecycle, Management, Reporting}
```

**Key point:** Both roles include `Supply Management`. That's **fine** — no constraint prevents it. They are unrelated roles (neither is a parent of the other). Grace gets `Supply Management` via both roles, but the union means it's present exactly once in her effective set. Union handles the deduplication automatically.

**Contrast with Scenario 3:** In Scenario 3, DocumentationTechnician could **not** include Asset Lifecycle even if Technician did, because they have a parent-child relationship. But SupplyTechnician and SupplyManager have no relationship, so overlap is allowed.

---

## Scenario 7: Removing a role from a user

**Situation:** A technician's documentation project ended; remove the specialization.

**Before:**
```
User: Casey Rodriguez
├─ Role: Technician
├─ Role: Documentation Technician (parent: Technician)
Effective: {Asset Lifecycle, Equipment Tracking, Field Work, Documentation Management, Report Generation}
```

**Admin action:** Remove `Documentation Technician` from Casey.

**After:**
```
User: Casey Rodriguez
├─ Role: Technician
Effective: {Asset Lifecycle, Equipment Tracking, Field Work}
```

**What happened:** Only the permission groups **unique to** Documentation Technician (Documentation Management, Report Generation) were removed. The permission groups that also belong to Technician stayed, because Casey still holds that role.

---

## Scenario 8: Attempting to remove a parent role (cascade delete)

**Situation:** Technician role has specializations. Admin wants to remove the Technician role from a user.

**Before:**
```
User: Casey Rodriguez
├─ Role: Technician
├─ Role: Documentation Technician (parent: Technician)
Effective: {Asset Lifecycle, Equipment Tracking, Field Work, Documentation Management, Report Generation}
```

**Admin action:** Remove `Technician` from Casey.

**System response:** Warning dialog shows:
```
⚠ Removing role "Technician" will also remove:
  └─ Documentation Technician (depends on Technician)

Confirm removal?
```

**User confirms.**

**After:**
```
User: Casey Rodriguez
(no roles)
Effective: {}
```

**What happened:** Because Documentation Technician depends on Technician, removing Technician also removes Documentation Technician. Both roles disappear.

---

## Scenario 9: Deleting a role from the system (role definition, not user assignment)

**Situation:** The organization decides the Safety Inspector specialization is no longer needed. Admin deletes the Safety Inspector role.

**System response:** Warning shows all users currently holding Safety Inspector:
```
⚠ Deleting role "Safety Inspector" will affect 7 users:
  ├─ Dana Kim
  ├─ Elena Patel
  ├─ ...
  └─ (7 users total)

Also check for dependent roles: None (Safety Inspector has no children).

Confirm deletion?
```

**User confirms.**

**Result:** The Safety Inspector role is removed from the system. All 7 users lose it. Their effective permission groups no longer include the Safety Inspector groups. If Safety Inspector was their only role, they have no roles.

---

## Scenario 10: Audit scenario — reviewing a user with permission creep

**Situation:** Admin is reviewing Grant Wilson's access.

**Current state:**
```
User: Grant Wilson
├─ Role: Technician (primary)
│  └─ groups: [Asset Lifecycle, Equipment Tracking, Field Work]
│  └─ Notes: "Hired 2026-01-01 as field technician."
│
├─ Role: Auditor (specialty)
│  └─ groups: [Audit Reports, Facility Access, Compliance Review]
│  └─ Notes: "Added 2026-02-15 for cross-team compliance project; review 2026-06-15."
│
├─ Role: Supply Manager (side_job)
│  └─ groups: [Supply Management, Management, Reporting]
│  └─ Notes: "Temporary; covering John's leave (until 2026-05-15)."
│
Effective: {Asset Lifecycle, Equipment Tracking, Field Work, Audit Reports, Facility Access, Compliance Review, Supply Management, Management, Reporting}
```

**Audit checklist:**
1. **Primary role clear?** Yes — Technician, hired as field tech.
2. **Specializations documented?** Yes — Auditor role added 2026-02-15 with sunset date 2026-06-15.
3. **Temporary roles have expiration?** Yes — Supply Manager until 2026-05-15.
4. **All roles justified?** Yes — notes explain each.
5. **Permission groups match roles?** Yes — all effective groups come from assigned roles, no drift.
6. **Any unusual access?** No — all roles are reasonable for this user's responsibilities.

**Conclusion:** Grant's access is clean and well-documented. Auditor can see at a glance why he has the access he does.

**Later audit (after review dates):**
1. Auditor checks — it's now 2026-06-20.
2. Grant's Auditor role sunset date (2026-06-15) has passed.
3. Admin action: Remove the Auditor role (and any dependent roles, if any).
4. Grant's roles revert to Technician + Supply Manager (until 2026-05-15).
5. Document the removal in the audit log.

---

## Scenario 11: Complex org with multiple role branches

**Situation:** A larger organization with several independent role trees.

**Role structure:**
```
Field Operations
  Technician
  ├─ Documentation Technician
  ├─ Hardware Specialist
  └─ Senior Technician

Compliance & Audit
  Auditor
  ├─ Compliance Auditor
  └─ Safety Auditor

Administration
  Manager
  └─ Operations Manager

IT & Infrastructure
  (no specializations)
  IT Support
  IT Manager
```

**Sample assignments:**
```
User: Hector Santos
├─ Technician (primary from Field Operations tree)
├─ Hardware Specialist (specialty from Field Operations tree)
└─ Safety Auditor (specialty from Compliance & Audit tree)
```

**Effective groups:** Union of all three roles.

**Key point:** Hector can hold roles from multiple independent trees (no cross-tree relationship). Each tree stands alone. If Field Operations deletes "Technician," then Hardware Specialist (which depends on it) is also deleted, but Safety Auditor (from a different tree) is unaffected.

---

## Related documents

- [concept.md](concept.md) — detailed explanation of concepts.
- [decisions.md](decisions.md) — why these design choices were made.
