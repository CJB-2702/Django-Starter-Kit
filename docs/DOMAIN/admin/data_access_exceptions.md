# Data Access Exceptions Log

This file logs **every deviation** from the [Golden Rule](DATA_OWNERSHIP.md#2-the-golden-rule) (access is determined strictly by Data Domain membership). It is maintained by hand.

Add an entry here when:

- A route or view filters by **organization** or **division** instead of (or in addition to) the `UserDomain` filter.
- A route or view grants access based on a permission group that was *not* the expected grant path (e.g. an IT role being used inside the Security application).
- A cross-boundary grant is intentionally wired into code (not just via operator-assigned domains).

---

## Format

Each entry is a short section with:

- **Route / view** — URL pattern and Python path.
- **Deviation** — what rule it breaks.
- **Reason** — why, in one or two sentences.
- **Mitigation** — how the deviation is audited (UI warning, log line, etc.).
- **Review date** — when this should be re-examined.

---

## Entries

*(No exceptions logged yet. All access currently flows through the Data Domain filter.)*

---

## Related documents

- [DATA_OWNERSHIP.md](DATA_OWNERSHIP.md) — the Golden Rule and the Data Domain primitive.
- [RBAC.md](RBAC.md) — Django-permission gates (action-level, not row-level).
- [permission_group_templates/concept.md](permission_group_templates/concept.md) — intentional cross-boundary grants and the notes field.
