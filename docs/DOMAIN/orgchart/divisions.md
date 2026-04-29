# Division → Organization map

This document lists every **division** in the application and the **organizations** that belong to it. It is a **human-maintained** reference used for onboarding and audit. For the conceptual rules around the hierarchy (and its informational-only status), see [../admin/DATA_OWNERSHIP.md](../admin/DATA_OWNERSHIP.md).

A skeleton of this file can be regenerated from the current database with:

```bash
python dev_tools/build_org_chart_skeleton.py
```

That script writes skeletons to `docs/DOMAIN/orgchart/` without overwriting human edits. Review the diff and merge manually.

---

## Divisions

*(Populate by running `build_org_chart_skeleton.py` and reviewing the output. The seed data ships with two divisions — North and South — each with two organizations.)*

- **North Division** (`north`)
  - North Acme Ltd — see [north-acme.md](north-acme.md)
  - North Beta Inc — see [north-beta.md](north-beta.md)
- **South Division** (`south`)
  - South Acme Ltd — see [south-acme.md](south-acme.md)
  - South Beta Inc — see [south-beta.md](south-beta.md)

---

## Related documents

- [../admin/DATA_OWNERSHIP.md](../admin/DATA_OWNERSHIP.md) — Data Domain primitive and Golden Rule.
- Per-organization sub-domain documents alongside this file (`<slug>.md`).
