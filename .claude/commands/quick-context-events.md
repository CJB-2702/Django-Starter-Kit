---
description: Load class/docstring context for the events application into this conversation.
---

Run the context extractor for the `events` application and read the YAML output into context.

```bash
python dev_tools/get_models_and_control.py --application events
```

Read the full YAML output. It lists every Python class with its docstring, and records non-Python files as present-only. Use this as a context summary for the events app — do not re-read individual files unless you need implementation detail. Briefly confirm which layers/directories were found and how many classes total.
