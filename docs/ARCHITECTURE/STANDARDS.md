# Project standards

## Vision

Create an application to manage assets and locations, track usage and assignments, and enforce **role-based access** to both **application capabilities** and **data**.

## Engineering principles

- Prefer **Django built-in** APIs and `django.contrib` packages; avoid new dependencies unless justified by an ADR in [DECISIONS/](DECISIONS/).
- Prefer **server-rendered HTML** with **Bulma** for layout and styling (vendored under [bulma-1.0.4/](../bulma-1.0.4/)).
- Use **HTMX** for dynamic interactions; prefer HTMX over ad hoc JavaScript for partial updates.

## Documentation

Product and technical specifications live under [docs/](readme.md). Start with [VISION.md](VISION.md) and [REQUIREMENTS.md](REQUIREMENTS.md).

UI layout, Bulma conventions, list formats, and accessibility baseline: [UX_UI.md](UX_UI.md).
