---
description: Load class/docstring context for the administration application into this conversation.
---

Run the context extractor for the `administration` application and read the YAML output into context.

```bash
python dev_tools/get_models_and_control.py --application administration
```

Read the full YAML output. It lists every Python class with its docstring, and records non-Python files as present-only. Use this as a context summary for the administration app — do not re-read individual files unless you need implementation detail. Briefly confirm which layers/directories were found and how many classes total.
