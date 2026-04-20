# Core application documentation

The **core** Django app holds shared domain models that other apps (maintenance, dispatch, supply, and so on) extend or reference. Documentation here focuses on **entities, required references, and interaction patterns**—not route-level authorization, which lives under [admin/](../admin/README.md).

| Document | Description |
|----------|-------------|
| [CORE_MODELS.md](CORE_MODELS.md) | Core tables, dependency rules, and how models interact |
| [core_dependencies.canvas](core_dependencies.canvas) | Obsidian canvas graph of must-have / optional links between core concepts |

Row-level **who may see which rows** is enforced using ownership groups and user assignments described in the administration docs: [DATA_OWNERSHIP.md](../admin/DATA_OWNERSHIP.md) and [USERS.md](../admin/USERS.md).
