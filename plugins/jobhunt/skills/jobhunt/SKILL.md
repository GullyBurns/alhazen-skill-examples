---
name: jobhunt
description: Track job applications, analyze positions, identify skill gaps, and plan your job search strategy
---

# Job Hunting Notebook Skill

Use this skill to manage your job search as a knowledge graph. Claude acts as your career coach, building understanding of positions, companies, and your fit over time.

**When to use:** "add job", "ingest job", "new position", "analyze this job posting", "show my pipeline", "skill gaps", "learning plan", "list positions", "update status", "job search"

## Prerequisites

- `uv` must be installed
- Docker must be running (TypeDB starts automatically on session start)

> **Path note:**
> - **Claude plugin install:** `<skill-path>` = `${CLAUDE_PLUGIN_ROOT}/skills/jobhunt`
> - **skillful-alhazen project:** `<skill-path>` = `.claude/skills/jobhunt`
>
> TypeDB starts automatically on session start (via SessionStart hook).
> No manual init required.

## Environment Variables

- `TYPEDB_HOST`: TypeDB server (default: localhost)
- `TYPEDB_PORT`: TypeDB port (default: 1729)
- `TYPEDB_DATABASE`: Database name (default: alhazen_notebook)

## Quick Start

```bash
# Ingest a job posting
uv run --project <skill-path> python <skill-path>/jobhunt.py ingest-job \
    --url "https://boards.greenhouse.io/anthropic/jobs/123456" \
    --priority high

# List your pipeline
uv run --project <skill-path> python <skill-path>/jobhunt.py list-pipeline
```

**Before executing any commands, read `USAGE.md` in this directory for the complete command reference, sensemaking workflow, data model, and automated foraging guide.**
