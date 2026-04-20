# Object-oriented control layer patterns

This document describes **common shapes** in the control layer so that:

- A new contributor can **predict the role of a class from its filename** before opening it.
- A new feature has a **near-mechanical playbook**: define a **Struct**, add **Context** methods, register a **Handler** or **Manager** when needed, gate with a **Guard** (a **Policy**, **Validator**, or **StateMachine**), narrate with **Narrator**, expose through **Adaptor**, and call from a **thin route**.

**Naming:** Prefer **class suffix vocabulary** (see below) and **long, explicit class and file names** that state what something is. **Do not use acronyms** in type or module names.

---

## 1. Class suffix vocabulary as a navigational aid

You name class shapes and **stick to them**. Anyone reading a filename knows the **shape and role** of the class inside before opening the file.

| Suffix | Typical role |
| :--- | :--- |
| **Struct** | Aggregated read model for one context: ids resolved, data loaded, `to_dict()` (or similar) for rendering. No business mutations. |
| **Context** | Entry point for control logic around one aggregate id (or key): loads a Struct, delegates to Managers and Handlers, owns the “story” of a workflow. |
| **Factory** | Stateless creation of **root** items (no parent); class methods; often returns a Struct or model instance. |
| **BulkFactory** | Batch creation; returns **only the highest-level created items** (not nested Structs). |
| **Handler** | Single-task specialist: one complex workflow step or command. |
| **Manager** | Domain or resource generalist: a stable sub-area of a Context (lifecycle, grouping of related operations). |
| **FactoryHandler** | Optional: when creation logic is heavy, group it behind one handler invoked from Context (see below). |
| **Policy** | **Guard** subtype — authorization or rule gate: “may this happen?” |
| **Validator** | **Guard** subtype — input or invariant checks at boundaries. |
| **Narrator** | Human-facing explanation, audit text, or comment text for logs and UI. |
| **Builder** | Stepwise construction for polymorphic children or workflows. |
| **StateMachine** | **Guard** subtype — explicit transitions for status-driven entities. |
| **Service** | Cross-cutting or integration operations (use sparingly; prefer Context + Manager). |
| **Adaptor** | Maps portal JSON, forms, or external payloads into **structured** types the control layer understands. |
| **Orchestrator** | Coordinates multiple steps across boundaries when a Context would be the wrong scope (rare). |

### Guard classes (Policy, Validator, StateMachine)

**Guard** is the shared **category** for types that **constrain** control flow: who may act (**Policy**), whether inputs and invariants hold (**Validator**), and which status transitions are legal (**StateMachine**). All three remain distinct **class suffixes** in code; the **Guard** name is how you group them in folders, reviews, and filenames.

**File naming:** `<class_name_stem>_guard.py` — the stem is the long, explicit snake_case name of the guard (usually aligned with the class name without the `Policy`, `Validator`, or `StateMachine` suffix). Example: `maintenance_event_close_guard.py` for a class such as `MaintenanceEventClosePolicy`. Do not use acronyms in the stem. One primary guard type per module is typical.

**Class naming:** Keep the vocabulary suffix on the class (`...Policy`, `...Validator`, `...StateMachine`) so imports and call sites stay self-explanatory.

**Docstring (required):** The **module docstring** or the **primary class docstring** must state:

1. **Which guard type** this is — Policy, Validator, or StateMachine.
2. **What** it guards (subject, aggregate, or transition), in one or two short sentences.

**Convention over configuration:** Naming does the work of a framework. No dependency-injection container, no plugin indirection — **disciplined imports** and **registries filled at import time** where needed.

---

## 2. Domain Struct pattern

**File naming:** `<item_name>_struct.py` (long, explicit `item_name`).

**Purpose:** Control and presentation often need the **same structured data** repeatedly for **one context** (e.g. one maintenance event id). The Struct:

- Takes the **base id** for that context.
- **Always** loads the **full row** for the base entity and **validates that it exists** (fail fast if missing).
- **Eager loads** related collections when `eager=True` (default), or exposes **lazy loaders** per slice when `eager=False`.

**Rules:**

- Structs **do not perform actions** (no creates, updates, deletes, side-effecting workflows). They **collect data** and may offer **lazy load** helpers for slices not yet loaded.
- Provide **`to_dict()`** (or equivalent) so templates and APIs get a stable, render-friendly shape.
- Optional properties: each related slice can have a **named accessor** that loads on demand if it was not eager loaded.

**Example (conceptual):** `MaintenanceEventStruct(id, eager=False)` always loads the full maintenance event row and validates it exists. Comments, attachments, actions, parts, and headers may be lazy-loaded through dedicated accessors when not eager loaded.

---

## 3. Context pattern

**Purpose:** All **control logic** flows through a Context tied to a natural key (usually an id).

**Initialization:**

- Accepts an id and an optional **`eager=True`** (or equivalent) to control Struct loading.
- Loads the appropriate **Struct** as the single source of structured data for the session.

**Usage style:** Prefer domain verbs on the Context instead of raw ORM in callers:

- **Good:** `MaintenanceEventContext(id).add_comment(data)`
- **Avoid:** Creating a comment row directly in a route while manually checking existence of the parent event.

**Alternate construction:** Contexts should expose a **`from_struct()`** class method so callers who **already built the Struct** can skip the usual init path and avoid duplicate queries.

---

## 4. Handlers versus Managers

Both are **orchestrators** in a loose sense, but **scope and lifecycle** differ.

| | **Handler** | **Manager** |
| :--- | :--- | :--- |
| **Scope** | **Single task** or complex step (one command, one conversion, one approval flow). | **Broader sub-domain** of the same aggregate (e.g. “everything about actions” for one event). |
| **Lifecycle** | Often created per call or used as a **named class** with a `create` / `run` entrypoint. | **Stable** collaborator on the Context: same aggregate, many operations over time. |
| **Analogy** | Specialist | Generalist for one resource slice |

**Context Managers (sub-managers on Context):** When a Context grows too large, **group related operations** and delegate to a **sub-manager** that receives the Context’s Struct (or the Context itself, per team convention). Group by **domain purpose**, not by file size alone.

**Example (conceptual):**

- `MaintenanceEventContext(id).action_manager.update_costs()`
- `MaintenanceEventContext(id).action_manager.get_completion_percentage()`

Prefer **Managers as properties** on the Context over **get_manager()**-style functions.

---

## 5. Context Handlers (complex single actions)

When **one** action is **too complex** for a single method, promote it to its own **Handler** class.

**Example (conceptual):**

- `MaintenanceEventContext(id).create_action(some_data)` — thin wrapper
- `MaintenanceEventContext(id).action_creation_handler.create(some_data)` — explicit Handler for the heavy path

Use one style consistently per feature; the important part is that **complexity has a named type and file**, not an anonymous 200-line method.

---

## 6. Factory pattern

**When:** Creating **complex root** items that have **no parent** (or the parent is the system).

**Rules:**

- Factories are **stateless**; expose **class methods** only (or a small, explicit surface).
- Factories often **return Structs** (or the primary model plus Structs), not loose dicts.

**Typical flow:**

1. The **presentation endpoint** extracts JSON or form data from the portal.
2. An **Adaptor** turns that into structured data: `structured_data = MaintenanceEventCreatePortalAdaptor(form, json_payload, ...)`.
3. The Factory creates the aggregate: `new_event_struct = MaintenanceEventFactory.create_event(structured_data)`.

**Prefer simple operations on the parent Context** for small writes (e.g. adding a comment) instead of a Factory.

---

## 7. Bulk Factory pattern

**When:** Batch creation of many items.

**Return shape:** Return **only a list of the highest-level items** created (e.g. events), **not** nested Structs for every child. Children may exist internally but are not the public return type.

**Example (conceptual):** `events = BulkMaintenanceEventFactory(data)` returns a list of events even if each event has comments or child rows created in the same transaction.

---

## 8. Factory Handlers and domain cohesion

Keep **domain logic close together**. When bulk or multi-step creation is still part of one bounded context, you may expose a **FactoryHandler** from the Context:

**Example (conceptual):** `MaintenanceEventContext.bulk_action_factory_handler.create_actions(data)` returns a list of actions.

This keeps routes thin while making the **operation name** greppable and testable.

---

## 9. Engineering principles (control layer)

- **Readability over brevity.** Long, explicit, **keyword-only** signatures over compact positional ones.
- **Composition over inheritance.** Inheritance is for **strategy interfaces**, not for reusing implementation details.
- **Convention over configuration.** Naming conventions replace frameworks; disciplined imports and import-time registries only where needed.
- **Explicit over magical.** No metaclass tricks, no implicit transactions, no hidden side effects on attribute setters.
- **Decomposition over consolidation.** Many small files over few large ones. When in doubt, **split**.
- **Domain verbs over CRUD verbs.** Methods are named after **business actions**, not database operations.
- **Tech debt is greppable.** Undesired shortcuts use **`# DELIBERATE ANTI-PATTERN`** blocks (with context), not silent acceptance.
- **One transaction per workflow.** Outer composition decides; inner calls cooperate with **`commit=False`** when appropriate.
- **No magic strings.** Status names, outcome types, and locked fields live in **class-level constants** and **frozen sets**.
- **Defensive at the edges, trusting in the middle.** Routes sanitize input and catch domain exceptions; once data is inside a **Context**, it is **trusted** for that operation.

---

## 10. Playbook for a new feature (checklist)

1. **Struct** — Define `<thing>_struct.py` with base row guaranteed, optional eager/lazy slices, `to_dict()`.
2. **Context** — Wire id + `from_struct()`, route all mutations through domain verbs.
3. **Manager** or **Handler** — Add a Manager for a sub-area of behavior; add a Handler for one heavy step.
4. **Guard** — Add a **Policy**, **Validator**, or **StateMachine** in `<name>_guard.py` (see Guard classes above); gate mutations and sensitive reads.
5. **Narrator** — Audit and user-visible strings where needed.
6. **Adaptor** — Map HTTP/portal payloads to structured constructor inputs at the boundary.
7. **Thin route** — Parse request, call Context, return response; **no writes** outside the control layer (see `layered_archetecture_rules.md`).

This aligns with **reads vs writes** rules in the layered architecture document: complex aggregates use Structs and search/loaders; **all persistence** stays in the control layer.
