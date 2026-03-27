# alhazen-skill-examples

Example skills for the [Skillful Alhazen](https://github.com/GullyBurns/skillful-alhazen) knowledge notebook framework — a TypeDB-powered scientific notebook for researchers building knowledge graphs from papers, notes, and domain data.

## What is this?

This repo serves two purposes:

1. **Claude Code plugin marketplace** — install skills directly into Claude Code (v1.0.33+) without a full Skillful Alhazen project. Each skill is a self-contained plugin with its own dependencies.
2. **Skillful Alhazen skills registry** — add skills to `skills-registry.yaml` in a Skillful Alhazen project and `make build-skills` wires them in.

---

## Skills

| Skill | Category | Description |
|-------|----------|-------------|
| [alhazen-core](skills/core/alhazen-core/) | core | **REQUIRED FIRST** — starts TypeDB, loads base schema |
| [jobhunt](skills/demo/jobhunt/) | demo | Track job applications, identify skill gaps, plan learning |
| [they-said-whaaa](skills/journalism/they-said-whaaa/) | journalism | Credibility tracker — ingest YouTube + news, detect contradictions |
| [scientific-literature](skills/biomed/scientific-literature/) | biomed | Multi-source literature search (EPMC, PubMed, OpenAlex, bioRxiv) |
| [alg-precision-therapeutics](skills/biomed/alg-precision-therapeutics/) | biomed | Rare disease mechanism investigation from a MONDO diagnosis |
| [literature-trends](skills/biomed/literature-trends/) | biomed | Trace hypothesis evolution across time windows in a literature cluster |

---

## Install via Claude Code Marketplace (recommended)

Requires Claude Code v1.0.33+.

### Step 1 — Install alhazen-core first

`alhazen-core` starts the TypeDB Docker container and loads the base schema that all other skills extend. **Every other skill depends on it.**

```
/plugins install https://github.com/sciknow-io/alhazen-skill-examples
```

Then initialize the infrastructure:

```
/alhazen-core:init
```

Expected output:
```json
{
  "success": true,
  "typedb": "running",
  "database": "alhazen_notebook",
  "schema": "loaded"
}
```

### Step 2 — Load a domain skill's schema

After `init`, each skill needs its own schema loaded once:

```bash
# Replace <skill-path> with your plugin cache path
# e.g. ~/.claude/plugins/cache/jobhunt/
uv run --project <skill-path> python <skill-path>/jobhunt.py init-schema
```

### Step 3 — Use the skill

```bash
uv run --project <skill-path> python <skill-path>/jobhunt.py list-pipeline
```

### Marketplace structure

The repo-level catalog is at [`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json). Each skill directory has a `.claude-plugin/plugin.json` declaring its name, version, license, and prerequisites.

```
.claude-plugin/
  marketplace.json          # Repo-level plugin catalog

skills/<category>/<name>/
  .claude-plugin/
    plugin.json             # Plugin metadata (name, version, license, requires)
  SKILL.md                  # Loaded at startup: triggers, quick start
  USAGE.md                  # Full reference: commands, workflows, data model
  skill.yaml                # Structured manifest
  <name>.py                 # CLI entry point (standalone, no external package deps)
  pyproject.toml            # uv-compatible dependency declaration
  schema.tql                # TypeDB schema extension (loaded via init-schema)
```

---

## Install via Skillful Alhazen (full project)

Add entries to `skillful-alhazen/skills-registry.yaml`:

```yaml
skills:
  - name: jobhunt
    git: https://github.com/sciknow-io/alhazen-skill-examples
    ref: main
    subdir: skills/demo/jobhunt

  - name: scientific-literature
    git: https://github.com/sciknow-io/alhazen-skill-examples
    ref: main
    subdir: skills/biomed/scientific-literature
```

Then build:

```bash
make build-skills   # clones skills into local_skills/, wires .claude/skills/ symlinks
make build-db       # loads all schemas (including new skill schemas) into TypeDB
```

In this mode, `make build-db` handles the base schema and all skill schemas automatically. The `alhazen-core` plugin is not needed.

---

## Prerequisites

| Requirement | Why |
|-------------|-----|
| [Docker](https://www.docker.com/) | Runs the TypeDB container |
| [uv](https://docs.astral.sh/uv/) | Runs skill Python CLIs with isolated deps |
| TypeDB 3.8.0+ | Launched by `alhazen-core init` or `make build-db` |

Optional per-skill:
- **they-said-whaaa**: `uv add youtube-transcript-api` for YouTube ingestion
- **scientific-literature**: `VOYAGE_API_KEY` + Qdrant for semantic search

---

## Skill File Structure

Every skill directory contains:

```
skills/<category>/<name>/
  SKILL.md          Slim discovery file (~30 lines): frontmatter, overview, triggers,
                    prerequisites, quick-start snippet, pointer to USAGE.md.
                    Loaded by Claude Code at startup for every conversation.
  USAGE.md          Full reference (read on demand): all commands, workflows,
                    data model, TypeDB patterns, sensemaking guidance, examples.
  skill.yaml        Structured manifest (name, description, operations, entity types)
  <name>.py         CLI entry point — self-contained, no skillful_alhazen package needed
  pyproject.toml    uv dependency declaration (run standalone with uv run --project .)
  schema.tql        TypeDB schema extension (sub-types of alhazen_notebook.tql)
  .claude-plugin/
    plugin.json     Claude Code marketplace metadata
```

**Why the SKILL.md / USAGE.md split?** Claude Code loads every `SKILL.md` into context at startup. Keeping them slim (~30 lines each) reduces static context overhead by ~90% vs. a single large file, while still giving Claude enough to select the right skill. Claude reads `USAGE.md` when it decides to actually use the skill.

**Self-contained CLIs:** Each skill's Python script includes all required utility functions inline (cache management, TypeQL helpers). `uv run --project <skill-dir>` installs only the skill's own deps — no `skillful_alhazen` package needed.

### `SKILL.md` format

```yaml
---
name: <skill-name>
description: <one-liner — when to use it, not just what it is>
---

# <Skill Name>

<2-3 sentences: what it does, when to use, Claude's role>

**Triggers:** <comma-separated trigger phrases>

## Prerequisites
...

## Quick Start
<2-4 key commands only — use <skill-path> placeholder>

**Before executing commands, read USAGE.md for the complete reference.**
```

### `plugin.json` format

```json
{
  "name": "<skill-name>",
  "display_name": "<Display Name>",
  "description": "<one-line description>",
  "version": "0.1.0",
  "license": "Apache-2.0",
  "requires": {
    "plugins": ["alhazen-core"],
    "system": {
      "bins": ["uv", "docker"],
      "description": "Run /alhazen-core:init first to set up TypeDB and base schema"
    }
  }
}
```

---

## Repo Structure

```
.claude-plugin/
  marketplace.json          # Repo-level plugin catalog (6 plugins)

skills/
  core/
    alhazen-core/           # Infrastructure: TypeDB setup + base schema
      alhazen_core.py       # CLI: init, status, reset
      alhazen_notebook.tql  # Base schema (copy of skillful-alhazen core schema)
      SKILL.md / USAGE.md / skill.yaml / pyproject.toml
      .claude-plugin/plugin.json

  demo/
    jobhunt/                # Job hunting notebook (reference implementation)
      jobhunt.py            # CLI: ingest-job, list-pipeline, show-gaps, ...
      SKILL.md / USAGE.md / skill.yaml / pyproject.toml / schema.tql
      .claude-plugin/plugin.json
      dashboard/            # Next.js components (for demo app)

  journalism/
    they-said-whaaa/        # Credibility and consistency tracker
      they_said_whaaa.py    # CLI: add-figure, ingest-youtube, add-claim, ...
      SKILL.md / USAGE.md / skill.yaml / pyproject.toml / schema.tql
      .claude-plugin/plugin.json
      dashboard/

  biomed/
    scientific-literature/  # Multi-source literature search and ingestion
      scientific_literature.py  # CLI: search, ingest, embed, search-semantic, ...
      SKILL.md / USAGE.md / skill.yaml / pyproject.toml / schema.tql
      .claude-plugin/plugin.json

    alg-precision-therapeutics/  # Rare disease investigation
      alg_precision_therapeutics.py  # CLI: init-investigation, ingest-disease, ...
      SKILL.md / USAGE.md / skill.yaml / pyproject.toml / schema.tql
      .claude-plugin/plugin.json

    literature-trends/      # Abductive argumentation analysis
      literature_trends.py  # CLI: create-thread, record-hypothesis, show-thread, ...
      SKILL.md / USAGE.md / skill.yaml / pyproject.toml / schema.tql
      .claude-plugin/plugin.json

  modeling/                 # Placeholder for future modeling skills

demo/                       # Shared Next.js base app
  docker-compose.yml        # Full stack: TypeDB + dashboard
  Dockerfile
  skills.config.ts          # Registry of installed skills for the demo
  src/app/                  # Hub page + skill pages
  src/lib/                  # Utility libraries
```

---

## Building a New Skill

See the [Alhazen Skill Architecture](https://github.com/GullyBurns/skillful-alhazen/wiki/Skill-Architecture) wiki for a full guide.

Quick checklist:

1. Copy the template: `cp -r skills/_template skills/<category>/<skill-name>`
2. Write `SKILL.md` (triggers, prereqs, quick start, pointer to USAGE.md)
3. Write `USAGE.md` (all commands, workflows, data model)
4. Write `skill.yaml` (name, operations, entity types)
5. Write `<skill-name>.py` — **inline all utilities** (copy cache + escape_string blocks from an existing skill; no `skillful_alhazen` imports)
6. Write `schema.tql` — extend `domain-thing`, `artifact`, `note`, etc. from the base schema
7. Write `pyproject.toml` with direct deps (`typedb-driver>=3.8.0`, `requests`, etc.)
8. Write `.claude-plugin/plugin.json` with `"requires": {"plugins": ["alhazen-core"]}`
9. Add to `.claude-plugin/marketplace.json`

The jobhunt skill is the reference implementation of the **curation pattern**:
1. **Foraging** — discover items of interest
2. **Ingestion** — fetch and store raw content
3. **Sensemaking** — Claude analyzes and annotates
4. **Analysis** — query across notes and entities
5. **Reporting** — dashboard views

---

## License

Apache-2.0
