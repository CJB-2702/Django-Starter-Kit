# Authorization Architecture — Design Decisions

This document outlines critical **trade-offs and operational decisions** for the two-gate authorization system (permissions + domains). It complements [ARCHITECTURE_SUMMARY.md](ARCHITECTURE_SUMMARY.md), which describes *what* the system is. This document addresses the *why* — the constraints and accepted risks behind design choices.

---

## Decision 1: Urgent Permission Revocation — Temporary Lockout Trade-off

**Decision:** When permissions or domains must be revoked urgently (e.g., contractor access termination, security incident), the system:
1. Identifies all users with **active sessions**.
2. Determines if they are affected by the revocation.
3. **Forcefully refreshes** their session state (clears and reloads `user_domain_ids` and `user_permission_codenames`).

**Accepted consequence:** During the refresh window (typically a few seconds), an affected user may be **temporarily locked out** if their permissions are revoked while they are mid-request.

**Why this, not alternatives:**

| Alternative | Trade-off |
|---|---|
| **Wait until session expiration** | Simpler (no forced refresh), but revocation is delayed until the user logs out or session TTL expires. For a contractor with active access, this could be hours or days. Unacceptable for security incidents. |
| **Per-request permission lookup (no session cache)** | Immediate revocation, but every request hits the database for permission checks. Prohibitive performance cost; session snapshot exists for this reason. |
| **Graceful session invalidation with warning message** | No lockout, but adds operational complexity: redirect to a "your access changed" page, require re-login. Still effective for urgent revocation, but more intrusive. |

**Rationale:** Session caching is necessary for performance. Urgent revocation is a rare but critical operation. The few-second lockout is **operationally acceptable** because:
- It is **time-bounded** and brief.
- It is **transparent** to the user (a single failed request, then re-login prompt).
- It is the **only safe way** to guarantee immediate revocation without per-request DB hits.
- **Real-world frequency:** Contractor offboarding, security incidents, and sensitive data leaks are rare; the lockout is an acceptable cost for those moments.

**Implementation note:** This behavior must be documented and communicated to operators. A notification system (audit log, admin alert) should surface when urgent revocations occur, so operators understand why a user may complain about brief lockouts.

---

## Decision 2: Domain Template Assignment — Additive by Default with Smart Removal

**Decision:** When a user is assigned a new domain template:
1. **New domains from the template are added** to the user's `UserDomain` set (additive).
2. **Existing domains are preserved** unless explicitly removed.
3. When a domain template is **removed** from a user's assignments:
   - The system checks if any **other active templates** assigned to that user contain the same domain.
   - If yes, the domain is **kept** in `UserDomain` (it is still supplied by another template).
   - If no, the domain is **removed** from `UserDomain`.

**Why this, not alternatives:**

| Alternative | Trade-off |
|---|---|
| **Rebase by default (replace old template)** | Simpler semantics for single-template users, but destructive for users with multiple domain templates. A user assigned both *Facility 1 Transportation* and *Cross-facility Auditor* could lose Facility 1 domains when reassigned (if rebase was triggered). Surprising and error-prone. |
| **Permanent accumulation (never remove domains)** | Safe (no data visibility loss), but leads to bloat. Domains accumulate over time; auditing becomes harder ("why does this user have 20 domains?"). |

**Rationale:** Real users often have **multiple, overlapping domain templates**. A technician might hold both *Facility 1 Transportation* (for their primary role) and *Cross-site Emergency Response* (for incident duty). Assigning a third template should not strip the first two. Smart removal ensures:
- **Multiple templates work intuitively** without surprises.
- **Domains aren't lost** due to template reassignment.
- **Drift is allowed** — admins can add/remove explicit `UserDomain` rows independently.
- **Audit is clear** — historical template assignment changes trace to domain changes.

---

## Decision 3: Role Cascade Delete — Mandatory Double Verification

**Decision:** When deleting a role that has dependent child roles, the system:
1. **Displays the full transitive tree** of all dependent roles before deletion.
2. **Requires explicit double verification** in the UI (e.g., "Type the role name to confirm" or a second confirmation button).
3. **Shows all affected users** who currently hold any of the dependent roles.
4. **Only commits** the cascade delete after both verifications are complete.

**Why double verification:**

Cascade delete is **destructive and transitive**:
- Deleting *Technician* removes *Technician* assignments from all users **and** removes all dependent *DocumentationTechnician*, *HardwareTechnician*, etc. roles from all users.
- This can affect dozens of users' access in seconds.
- Unlike domain removal (which leaves data visible but uneditable), a permission removal is a **capability loss** that may break users' workflows.

**Why this, not alternatives:**

| Alternative | Trade-off |
|---|---|
| **No double verification (warn, single confirmation)** | Faster for admins, but a misclick or brief distraction could trigger mass access revocation. One confirmation is insufficient for an action affecting 50+ users. |
| **Soft constraint (warn, but allow archival instead)** | Archival preserves history but leaves orphaned roles in the system. Admins encounter them later and are confused. Hard to clean up old roles. |
| **Prevent cascade entirely** | Forces reassignment of all child roles before parent deletion. Much safer, but operationally complex ("reassign X roles before you can delete Y"). In practice, this often means never deleting roles, which defeats the purpose. |

**Rationale:** Mass access revocation is rare but high-impact. Double verification is the **minimal procedural gate** that prevents accidental cascade deletes without adding significant overhead for intentional ones. The list of affected users serves as a **final sanity check** for the operator.

**Implementation note:** The UI must be **clear and hard to misuse**:
- Display role name, dependent roles, affected user count prominently.
- Use a typed-confirmation or multi-button pattern (not a single checkbox).
- Log the deletion with operator ID, timestamp, and the full tree that was deleted.

---

## Decision 4: Data-Access Exceptions — Manual Tracking, Actively Maintained

**Decision:** Routes or views that deviate from the Golden Rule (access is determined by domain membership + permission) are **manually logged** in [data_access_exceptions.md](data_access_exceptions.md).

**Maintenance:** The exception log is **actively maintained by humans** as the codebase evolves:
- When a new route deviates from the Golden Rule, the deviation is **explicitly documented** (route, reason, exception type).
- Code reviews flag new routes that break the rule; the exception is documented or the route is fixed.
- The exception log is **not auto-generated**; manual curation prevents the log from becoming stale or bloated.

**Why manual, not automated:**

| Alternative | Trade-off |
|---|---|
| **Automated scanning for rule violations** | Catches violations but produces false positives (filters that happen to also check org-level are not violations). Requires extensive heuristics. Easy to ignore (scan results in a CI log). |
| **No tracking; hope engineers remember** | Some violations go undocumented; audit trail is incomplete. Hard to review total exception count. |

**Rationale:** The Golden Rule is **conceptually simple** but **enforcement is manual** (developers must think about it). The exception log is a **human-maintained registry** of intentional deviations, which serves three purposes:
1. **Audit:** Reviewers can see at a glance which routes break the rule and why.
2. **Refactoring target:** Routes in the log are candidates for cleanup or architectural change.
3. **Compliance:** Organizations with strict data-access requirements can audit these exceptions during compliance reviews.

**Operational cost:** Low. The log grows slowly (new exceptions are rare). Code review discipline ensures new routes are either compliant or explicitly documented.

---

## Summary: Trade-offs Accepted

| Decision | Accepted Risk | Mitigation |
|---|---|---|
| Urgent revocation | Temporary lockout (few seconds) | Transparent to user; brief; rare; documented in audit log |
| Additive domain templates | Domain bloat if not reviewed | Periodic access reviews; drift tracking visible in UI |
| Cascade delete | Mass permission loss | Double verification UI; affected user list; audit log |
| Manual exception tracking | Log falls out of sync | Code review discipline; human curation; not auto-generated |

---

## Related documents

- [ARCHITECTURE_SUMMARY.md](ARCHITECTURE_SUMMARY.md) — the complete authorization architecture.
- [RBAC.md](RBAC.md) — permission system concepts.
- [DATA_OWNERSHIP.md](DATA_OWNERSHIP.md) — domain system concepts.
- [roles/decisions.md](roles/decisions.md) — role-specific design decisions.
- [data_access_exceptions.md](data_access_exceptions.md) — log of routes deviating from the Golden Rule.
