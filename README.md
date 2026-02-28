# alhazen-skill-examples

Example skills for the [Alhazen](https://github.com/GullyBurns/skillful-alhazen) knowledge notebook framework.

## What is this?

This repo serves two purposes:

1. **Installable skill registry** — add it to your `skills-registry.yaml` and `make skills-install` copies skills into your project
2. **Reference and demo** — well-documented examples showing how to build Alhazen skills, with a runnable shared demo dashboard

## Skills

| Skill | Category | Description |
|-------|----------|-------------|
| [jobhunt](skills/demo/jobhunt/) | demo | Track job applications, analyze positions, identify skill gaps |
| [techrecon](skills/demo/techrecon/) | demo | Systematically investigate software systems, libraries, and frameworks |
| [epmc-search](skills/biomed/epmc-search/) | biomed | Search PubMed/Europe PMC, build literature corpora |
| [apm](skills/biomed/apm/) | biomed | Investigate rare disease cases using the Algorithm for Precision Medicine |
| [rare-disease](skills/biomed/rare-disease/) | biomed | Build a 360° knowledge graph for a known rare disease from a MONDO ID |

## Install a Skill

Add entries to your `skillful-alhazen/skills-registry.yaml`:

```yaml
skills:
  - name: jobhunt
    git: https://github.com/GullyBurns/alhazen-skill-examples
    ref: main
    subdir: skills/demo/jobhunt

  - name: rare-disease
    git: https://github.com/GullyBurns/alhazen-skill-examples
    ref: main
    subdir: skills/biomed/rare-disease
```

Then install:

```bash
make skills-install
```

## Skill File Structure

Every skill directory contains two documentation files:

```
skills/<category>/<name>/
  SKILL.md    — slim discovery file (~30 lines): frontmatter, overview, triggers,
                prerequisites, quick-start snippet, pointer to USAGE.md.
                Loaded by Claude Code at startup for every conversation.
  USAGE.md    — full reference (read on demand): all commands, workflows,
                data model, TypeDB patterns, sensemaking guidance, examples.
                Claude reads this when it decides to use the skill.
```

**Why the split?** Claude Code loads every `SKILL.md` into context at startup. Keeping them slim (~30 lines each) reduces static context overhead by ~90% compared to a single large file, while still giving Claude enough to select the right skill. When Claude invokes a skill it reads `USAGE.md` for the full execution details.

**`SKILL.md` format:**

```yaml
---
name: <skill-name>
description: <one-liner — when to use it, not just what it is>
---

# <Skill Name>

<2–3 sentences: what it does, when to use, Claude's role>

**Triggers:** <comma-separated trigger phrases>

## Prerequisites
...

## Quick Start
<2–4 key commands only>

**Before executing commands, read `USAGE.md` in this directory for the complete reference.**
```

## Run the Demo

```bash
# 1. Assemble symlinks from skills into demo app
make demo-sync

# 2. Start the full stack (TypeDB + dashboard)
cd demo && docker compose up
```

The dashboard opens at http://localhost:3000.

## Repo Structure

```
skills/
  demo/
    jobhunt/            # Job hunt skill (fully implemented reference)
      SKILL.md          # Slim: frontmatter, overview, triggers, quick start
      USAGE.md          # Full: commands, workflows, data model, dashboard
      skill.yaml        # Skill manifest
      schema.tql        # TypeDB schema
      jobhunt.py        # Main CLI
      job_forager.py    # Automated job discovery
      job_triage.py     # Candidate triage
      dashboard/        # Web UI components (assembled via make demo-sync)
    techrecon/          # Tech recon skill
      SKILL.md / USAGE.md / skill.yaml / schema.tql / techrecon.py

  biomed/
    epmc-search/        # Europe PMC literature search skill
      SKILL.md / USAGE.md / skill.yaml / schema.tql / epmc_search.py
    apm/                # Algorithm for Precision Medicine skill
      SKILL.md / USAGE.md / skill.yaml / schema.tql / apm.py
    rare-disease/       # Rare disease knowledge graph skill
      SKILL.md / USAGE.md / skill.yaml / schema.tql / rare_disease.py

  modeling/             # Future: domain modeling skill

demo/                   # Shared Next.js base app
  docker-compose.yml    # Full stack: TypeDB + dashboard
  Dockerfile
  skills.config.ts      # Registry of installed skills
  src/app/              # Hub page + skill pages (assembled via make demo-sync)
  src/components/ui/    # shadcn/ui base components
  src/lib/              # Utility libraries (skill libs assembled via make demo-sync)
```

## Building a New Skill

See the [Alhazen Skill Architecture](https://github.com/GullyBurns/skillful-alhazen/wiki/Skill-Architecture) wiki for a full guide.

The jobhunt skill is the reference implementation of the **curation pattern**:
1. **Foraging** — discover items of interest
2. **Ingestion** — fetch and store raw content
3. **Sensemaking** — Claude analyzes and annotates
4. **Analysis** — query across notes and entities
5. **Reporting** — dashboard views

## License

Apache-2.0
