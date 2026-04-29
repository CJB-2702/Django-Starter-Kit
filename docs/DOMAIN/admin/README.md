# Administration application documentation

The **admin** Django app (and related configuration) owns **identity and access**: Django's user, permission, and group tables; **roles** that bundle Django groups; **domain templates** that bundle Data Domains; and the **Data Domain** primitive that ties users to row-level scope. Core business entities (assets, events, part demands, and so on) live in the **core** app; see [core/README.md](../core/README.md).

## Start here

- **[ARCHITECTURE_SUMMARY.md](ARCHITECTURE_SUMMARY.md)** — The complete system at a glance: two orthogonal access gates (permission + scope), session snapshot, audit trail, constraints, and a summary table.

## Documentation by topic

| Document | Description |
|----------|-------------|
| [ARCHITECTURE_DECISIONS.md](ARCHITECTURE_DECISIONS.md) | **Design decisions & trade-offs:** urgent revocation, additive templates, cascade delete verification, exception tracking |
| [RBAC.md](RBAC.md) | Django permissions and permission groups; **roles**; what Django auth does *not* cover |
| [DATA_OWNERSHIP.md](DATA_OWNERSHIP.md) | The **Data Domain** primitive and the Golden Rule; divisions and organizations as informational hierarchy; **domain templates** |
| [USERS.md](USERS.md) | User model concerns: data domain assignments, session snapshot, auditing dependency, template metadata |
| [roles/concept.md](roles/concept.md) | Business concept and rules for roles (job profiles, permission groups, inheritance, cascade delete, multiple assignment, storytelling) |
| [roles/decisions.md](roles/decisions.md) | Design decisions behind the role system (why multiple roles, single-layer inheritance, union semantics, etc.) |
| [roles/examples.md](roles/examples.md) | Common role assignment scenarios and how they work in practice |
| [domain_templates/concept.md](domain_templates/concept.md) | Business concept and rules for domain templates (scope profiles, additive assignment, audit history) |
| [domain_templates/models_and_control_layer_updates.md](domain_templates/models_and_control_layer_updates.md) | Architectural plan: domain template models, control-layer classes, guards, UI entrypoints |
| [data_access_exceptions.md](data_access_exceptions.md) | Log of routes/views that deviate from the Golden Rule (filter by org/div, cross-sector grant, etc.) |

See also `docs/DOMAIN/orgchart/` for the division/organization/domain tree and per-organization sub-domain breakdowns.
