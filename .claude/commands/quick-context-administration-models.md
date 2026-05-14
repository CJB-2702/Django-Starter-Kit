---
description: Load class/docstring context for administration/models into this conversation.
---

Run the context extractor for the `administration` application — models layer only — and read the YAML output into context.

```bash
python dev_tools/get_models_and_control.py --application administration --models_only
```

Read the full YAML output. It lists every model class with its docstring. Use this as a context summary — do not re-read individual files unless you need implementation detail. Briefly confirm which model classes were found.
