---
name: alhazen-core
description: REQUIRED FIRST — sets up TypeDB container and loads the Alhazen base schema. Must run before any other Alhazen skill.
---

# Alhazen Core

**Install and initialize this skill before any other Alhazen skill.**

Sets up the shared TypeDB infrastructure: starts the TypeDB Docker container and loads `alhazen_notebook.tql` (the base schema that all domain skills extend).

**When to use:** First-time setup, infrastructure health checks, resetting the database.

## Prerequisites

- Docker must be running
- `uv` must be installed

## Quick Start

```bash
# Replace <skill-path> with your installation directory
# e.g. ~/.claude/plugins/cache/alhazen-core/

# Initialize everything (idempotent — safe to re-run)
uv run --project <skill-path> python <skill-path>/alhazen_core.py init

# Check status
uv run --project <skill-path> python <skill-path>/alhazen_core.py status
```

Expected output from `init`:
```
{"success": true, "typedb": "running", "database": "alhazen_notebook", "schema": "loaded"}
```

**After init, load each skill's schema:** each domain skill has an `init-schema` command that loads its own `schema.tql`.

**Read `USAGE.md` for troubleshooting and advanced usage.**
