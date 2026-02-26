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

## Install a Skill

Add this registry to your `skillful-alhazen/skills-registry.yaml`:

```yaml
skills:
  - name: jobhunt
    git: https://github.com/GullyBurns/alhazen-skill-examples
    ref: main
    subdir: skills/demo/jobhunt
```

Then install:

```bash
make skills-install
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
  demo/jobhunt/           # Job hunt skill (fully implemented)
    SKILL.md              # Claude's instructions
    skill.yaml            # Skill manifest
    schema.tql            # TypeDB schema
    pyproject.toml        # Self-contained Python deps
    jobhunt.py            # Main CLI
    job_forager.py        # Automated job discovery
    job_triage.py         # Candidate triage
    dashboard/            # Web UI components (assembled via make demo-sync)
      components/
      routes/
      pages/
      lib.ts
  modeling/               # Future: domain modeling skill
  biomed/                 # Future: biomedical analysis skill

demo/                     # Shared Next.js base app
  docker-compose.yml      # Full stack: TypeDB + dashboard
  Dockerfile
  skills.config.ts        # Registry of installed skills
  src/app/                # Hub page + skill pages (assembled via make demo-sync)
  src/components/ui/      # shadcn/ui base components
  src/lib/                # Utility libraries (skill libs assembled via make demo-sync)
```

## Building a New Skill

See the [Alhazen Skill Architecture](https://github.com/GullyBurns/skillful-alhazen/wiki/Skill-Architecture) wiki for a full guide.

The jobhunt skill is the reference implementation of the **curation pattern**:
1. **Foraging** — discover jobs
2. **Ingestion** — fetch and store raw descriptions
3. **Sensemaking** — Claude analyzes content
4. **Analysis** — query across notes
5. **Reporting** — dashboard views

## License

Apache-2.0
