# Administration application documentation

The **admin** Django app (and related configuration) owns **identity and access**: Django’s user, group, and permission tables; **group templates** that bundle Django groups; and the **data ownership** model that ties users to ownership groups for row-level scope. Core business entities (assets, events, part demands, and so on) live in the **core** app; see [core/README.md](../core/README.md).

| Document | Description |
|----------|-------------|
| [RBAC.md](RBAC.md) | Django groups and permissions, group templates, and what stock auth does *not* cover |
| [DATA_OWNERSHIP.md](DATA_OWNERSHIP.md) | Divisions, organizations, ownership groups as scope; overlap; relation to core row FKs |
| [USERS.md](USERS.md) | User model concerns: ownership assignment, session, auditing dependency, template metadata |
