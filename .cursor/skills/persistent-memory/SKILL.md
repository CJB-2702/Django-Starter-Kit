---
name: persistent-memory
description: Appends a one-line work log to the repo root file memory.md after substantive assistant turns. Use on every coding session in this project and whenever completing edits, fixes, or tasks that should leave a minimal paper trail.
---

# Persistent memory (`memory.md`)

## When to write

After you finish meaningful work in a turn (code or config changes, migrations, fixes, notable decisions, or completed multi-step tasks). **Skip** for pure Q&A, acknowledgments, or when nothing was done.

## What to write

- **One short line** (roughly one sentence). Plain text; no markdown headings or bullets in the log line.
- **Minimal content only**: what changed or was decided — not a transcript, not rationale, not file lists unless one file name is the whole story.
- **Append** to `memory.md` at the **repository root** (`memory.md`). Create the file if it does not exist.
- **Newest last** (append at end). Optional date prefix `YYYY-MM-DD — ` if it helps scanning; keep the line short either way.

## Examples

Good:

- `2026-04-18 — Fixed login redirect; added test for staff-only route.`
- `Added persistent-memory skill; append-only log in memory.md.`

Bad (too long or wrong):

- Multi-paragraph recap of the conversation
- Copy-paste of error stacks or full diffs
- Repeating the same entry if you already logged the same work in this session (one line per discrete chunk of work is enough)

## Conflicts with other instructions

If another rule says not to edit markdown without a user request, **this file is the exception**: updating `memory.md` is allowed and expected when this skill applies.
