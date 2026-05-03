---
name: jobhunt
description: Track job applications, analyze positions, identify skill gaps, and plan your job search strategy
read_strategy: |
  On first use: read Quick Start.
  When ingesting: read Ingestion + Sensemaking sections.
  When analyzing: read Analysis section.
  Full command reference: read Commands section on demand.
triggers:
  - add job / ingest job / new position
  - analyze this job posting / make sense of
  - show my pipeline / skill gaps / learning plan
  - update status / job search
prerequisites:
  - TypeDB running (make db-start)
  - make build-skills
---

# Job Hunting Notebook Skill

Use this skill to manage your job search as a knowledge graph. Claude acts as your career coach, building understanding of positions, companies, and your fit over time.

---

## 1. Quick Start

### Prerequisites

- TypeDB must be running: `make db-start`
- Dependencies installed: `uv sync --all-extras` (from project root)
- Schema loaded: run `make build-db` after `make build-skills`

> **Path note:** Replace `.claude/skills/jobhunt` below with your installation directory:
> - **Claude plugin install:** `${CLAUDE_PLUGIN_ROOT}/skills/jobhunt` (self-contained bundle at `plugins/jobhunt/`)
> - **skillful-alhazen project:** `.claude/skills/jobhunt`
>
> When installed as a plugin, TypeDB starts automatically on session start (no manual init required).

### Environment Variables

- `TYPEDB_HOST`: TypeDB server (default: localhost)
- `TYPEDB_PORT`: TypeDB port (default: 1729)
- `TYPEDB_DATABASE`: Database name (default: alhazen_notebook)

### Essential Commands

```bash
# Ingest a job posting from URL
uv run python .claude/skills/jobhunt/jobhunt.py ingest-job \
    --url "https://boards.greenhouse.io/anthropic/jobs/123456" \
    --priority high

# List your pipeline
uv run python .claude/skills/jobhunt/jobhunt.py list-pipeline

# Show position details
uv run python .claude/skills/jobhunt/jobhunt.py show-position --id "position-abc123"

# Add a note to any entity
uv run python .claude/skills/jobhunt/jobhunt.py add-note \
    --about "position-abc123" --type research \
    --content "Strong AI safety focus, good culture fit"
```

### Command Output Pattern

`uv run` emits a `VIRTUAL_ENV` warning to stderr. Always use `2>/dev/null` when piping output to a JSON parser -- never `2>&1`, which merges the warning into stdout and breaks JSON parsing.

---

## 2. Your Skill Profile

Before analyzing jobs, set up your skill profile for gap analysis.

### Add Your Skills

```bash
uv run python .claude/skills/jobhunt/jobhunt.py add-skill \
    --name "Python" --level "strong"

uv run python .claude/skills/jobhunt/jobhunt.py add-skill \
    --name "Distributed Systems" --level "some" \
    --description "Built caching layer, some k8s experience"

uv run python .claude/skills/jobhunt/jobhunt.py add-skill \
    --name "Rust" --level "learning"
```

**Skill levels:** `strong` | `some` | `learning` | `none`

### View Your Skills

```bash
uv run python .claude/skills/jobhunt/jobhunt.py list-skills
```

---

## 3. Discovery

### Automated Foraging (Job Forager)

Automates discovery by searching job boards and aggregators, filtered by your skill profile.

#### Setup: Add Search Sources

```bash
# Company board sources
uv run python .claude/skills/jobhunt/job_forager.py add-source \
    --name "Anthropic" --platform greenhouse --token anthropic

# Aggregator sources
uv run python .claude/skills/jobhunt/job_forager.py add-source \
    --name "ML Jobs" --platform linkedin --query "machine learning" --location "San Francisco"
uv run python .claude/skills/jobhunt/job_forager.py add-source \
    --name "Remote ML" --platform remotive --query "machine learning"
```

#### Search and Heartbeat

```bash
# Search one source
uv run python .claude/skills/jobhunt/job_forager.py search-source --source "ML Jobs"

# Full heartbeat: search all sources, filter, dedup, store
uv run python .claude/skills/jobhunt/job_forager.py heartbeat --min-relevance 0.1
```

#### Triage Candidates

```bash
uv run python .claude/skills/jobhunt/job_forager.py list-candidates --status new
uv run python .claude/skills/jobhunt/job_forager.py triage --id candidate-abc123 --action reviewed
uv run python .claude/skills/jobhunt/job_forager.py promote --id candidate-abc123
```

#### Platform Details

| Platform | Type | Auth | Args |
|----------|------|------|------|
| `greenhouse` | Company board | None | `--token` (slug) |
| `lever` | Company board | None | `--token` (slug) |
| `ashby` | Company board | None | `--token` (slug) |
| `linkedin` | Aggregator | None | `--query`, `--location` |
| `remotive` | Aggregator | None | `--query`, `--location` |
| `adzuna` | Aggregator | API key | `--query`, `--location` |

### Web Search for Opportunities

Use the `web-search` skill to find opportunities not covered by automated foraging. Search for company career pages, niche job boards, or specific role types.

---

## 4. Ingestion

### From URL (ingest-job)

**Triggers:** "add job", "ingest job", "new position", "found a job posting", "here's a job"

```bash
uv run python .claude/skills/jobhunt/jobhunt.py ingest-job \
    --url "https://boards.greenhouse.io/anthropic/jobs/123456" \
    --priority high \
    --tags "ai" "ml" "safety"
```

**Options:**
- `--url` (required): Job posting URL
- `--priority`: Set priority (high/medium/low)
- `--tags`: Space-separated tags

**Returns:**
```json
{
  "success": true,
  "position_id": "position-abc123",
  "artifact_id": "artifact-xyz789",
  "status": "raw",
  "message": "Artifact stored - ask Claude to 'analyze this job posting' for sensemaking."
}
```

**What ingestion produces:**
- A `jobhunt-position` entity with status `researching`
- A `jobhunt-job-description` artifact containing the raw scraped page content
- An initial `jobhunt-application-note` tracking the application status

### Manual Position (add-position)

```bash
uv run python .claude/skills/jobhunt/jobhunt.py add-position \
    --title "Senior ML Engineer" \
    --company "Anthropic" \
    --priority high
```

### Add Company

```bash
uv run python .claude/skills/jobhunt/jobhunt.py add-company \
    --name "Anthropic" \
    --url "https://anthropic.com" \
    --description "AI safety research company"
```

### Add Engagement

```bash
uv run python .claude/skills/jobhunt/jobhunt.py add-engagement \
    --name "Acme Corp Data Consulting" \
    --company-id "company-abc123" \
    --type project \
    --rate "$200/hr" \
    --status active \
    --priority high
```

**Engagement types:** `hourly` | `project` | `retainer` | `advisory`

### Add Venture

```bash
uv run python .claude/skills/jobhunt/jobhunt.py add-venture \
    --name "Augura Health Advisory" \
    --stage proposal-sent \
    --equity-type advisor \
    --priority high
```

**Venture stages:** `exploring` | `proposal-sent` | `negotiating` | `active` | `paused` | `closed`
**Equity types:** `none` | `advisor` | `cofounder` | `investor`

### Add Lead

```bash
uv run python .claude/skills/jobhunt/jobhunt.py add-lead \
    --name "Jane Smith - BigCo" \
    --status warm \
    --priority medium \
    --description "Met at ML Summit, interested in consulting"
```

**Lead statuses:** `first-contact` | `active` | `inactive` | `closed`

---

## 5. Sensemaking

### Sensemaking Workflow

**When user says "analyze this job posting" or "make sense of [position]":**

1. **Get the artifact content**
   ```bash
   uv run python .claude/skills/jobhunt/jobhunt.py show-artifact --id "artifact-xyz"
   ```

2. **Read and comprehend the content**
   - Look for: company name, job title, location, salary, remote policy
   - Identify: requirements, responsibilities, qualifications
   - Note: team info, culture signals, growth opportunities

3. **Research the company and leadership online** (use the web-search skill)

   Search for: company mission, funding, recent news, and LinkedIn activity of key leaders.
   Focus on:
   - **Company:** founding story, funding/investors, mission statement, recent product launches
   - **Leadership:** CEO, CTO, relevant SVPs -- what are they posting about on LinkedIn?
   - **Role context:** Which leader is likely the hiring manager? What technical bets is the team making?
   - **Culture signals:** hiring pace, public talks, open-source releases, AI-in-residence programs

   Save findings as a research note attached to **both** the company and the position:
   ```bash
   # Company-level research (background, funding, mission)
   uv run python .claude/skills/jobhunt/jobhunt.py add-note \
       --about "company-xyz" \
       --type research \
       --content "Series C, $4B raised. Mission: X. CEO recently spoke at Y conference..."

   # Position-level research (leadership context, role fit signals, hiring manager)
   uv run python .claude/skills/jobhunt/jobhunt.py add-note \
       --about "position-abc123" \
       --type research \
       --content "Bo Wang (SVP Biomedical AI) is likely hiring manager. Very active on LinkedIn..."
   ```

4. **Create/update the company**
   ```bash
   uv run python .claude/skills/jobhunt/jobhunt.py add-company \
       --name "Anthropic" \
       --url "https://anthropic.com" \
       --description "AI safety research company"
   ```

5. **Extract requirements as fragments**
   ```bash
   uv run python .claude/skills/jobhunt/jobhunt.py add-requirement \
       --position "position-abc123" \
       --skill "Python" \
       --level "required" \
       --your-level "strong" \
       --content "5+ years Python experience, focus on ML systems"
   ```

6. **Create analysis notes**

   **Fit Analysis Note:**
   ```bash
   uv run python .claude/skills/jobhunt/jobhunt.py add-note \
       --about "position-abc123" \
       --type fit-analysis \
       --content "Strong fit for core requirements. Gap in distributed systems." \
       --fit-score 0.82 \
       --fit-summary "Strong technical fit, one gap to address"
   ```

   **Skill Gap Note:**
   ```bash
   uv run python .claude/skills/jobhunt/jobhunt.py add-note \
       --about "position-abc123" \
       --type skill-gap \
       --content "Distributed systems is required. Recommend: DDIA book, MIT 6.824 course."
   ```

7. **Flag uncertainties**
   ```bash
   uv run python .claude/skills/jobhunt/jobhunt.py tag \
       --entity "requirement-xyz" \
       --tag "uncertain"
   ```

8. **Report findings to user**: company overview, leadership signals, fit score breakdown, key gaps, suggested next steps (including who to follow on LinkedIn)

### List Artifacts Needing Analysis

```bash
uv run python .claude/skills/jobhunt/jobhunt.py list-artifacts --status raw
uv run python .claude/skills/jobhunt/jobhunt.py list-artifacts --status all
```

### Get Artifact Content

```bash
uv run python .claude/skills/jobhunt/jobhunt.py show-artifact --id "artifact-xyz789"
```

### Quality Checklist

Every opportunity MUST have after sensemaking:

- **Clean title** -- strip "Job Application for", "| LinkedIn", "hiring", and other job-board boilerplate from the name
- **Short-name** -- a compact display label (3-4 words, e.g. "Sr ML Eng - Anthropic")
- **Company linked** -- via `--company` flag on add-position, auto-matched to existing `jobhunt-company` entities (do not create duplicates)
- **Salary/compensation researched** -- if not in the posting, search Levels.fyi or Glassdoor and record in `salary-range` attribute
- **At least one research note** -- company background, leadership, role context
- **Requirements extracted** -- as `jobhunt-requirement` entities via `add-requirement`
- **Fit analysis note** -- with `fit-score` (0.0-1.0) and `fit-summary`
- **Opportunity summary** -- a `jobhunt-opp-summary-note` synthesizing all notes. Regenerated after any note is added or updated.
- **Embedded in map** -- run `embedding_map.py embed-and-map` after saving the summary so the opportunity appears on Mission Control.

### Opportunity Summary

Every opportunity has exactly one `jobhunt-opp-summary-note` — a living markdown dossier that is overwritten each time notes change. This is the primary embedding text for the Mission Control map and the quick-read view for understanding any opportunity.

**Workflow — regenerate after any note update:**
```bash
# 1. Fetch all notes + metadata
uv run python .claude/skills/jobhunt/jobhunt.py regenerate-summary --about <opp-id>

# 2. Read the JSON output, write a markdown summary following the template below

# 3. Save the summary (creates or overwrites)
uv run python .claude/skills/jobhunt/jobhunt.py upsert-summary --about <opp-id> --content "@/tmp/summary.md"

# 4. Re-embed to update the Mission Control map
uv run python local_skills/jobhunt/embedding_map.py embed-and-map
```

**IMPORTANT:** Step 4 (re-embed) MUST be run after saving the summary. Without it, new or updated opportunities will not appear on the Mission Control map. This step re-computes embeddings for ALL opportunities and regenerates the 2D layout.

**Summary templates by type:**

**Position:**
```markdown
## Role
- Title, company, location/remote policy
- Key responsibilities (2-3 bullets)
- Salary range if known

## Fit
- Overall fit score and one-line assessment
- Top strengths (2-3 bullets with specifics)
- Key gaps (1-2 bullets)

## Company
- What they do, stage/size, why interesting
- Key people (hiring manager, contacts)

## Status
- Current application status
- Key dates, next steps, or outcome
```

**Engagement:**
```markdown
## Engagement
- Client, scope, type (consulting/contract/advisory)
- Rate/compensation if known

## Fit
- Why this is a good match
- Key deliverables

## Status
- Current stage (proposal/active/paused/closed)
```

**Venture:**
```markdown
## Overview
- What the venture is, stage
- Your role/involvement

## Opportunity
- Why it's interesting
- Key milestones or next steps

## Status
- Current stage (seed/series-a/series-b/growth/closed)
```

**Lead:**
```markdown
## Contact
- Who, title, organization
- How you met, when

## Context
- What the connection is about
- Potential opportunity or value

## Status
- Relationship state (first-contact/active/inactive/closed)
```

---

## 6. Application Tracking

### Update Status

```bash
uv run python .claude/skills/jobhunt/jobhunt.py update-status \
    --position "position-abc123" \
    --status "applied" \
    --date "2025-02-05"
```

**Status values:** `researching` | `applied` | `phone-screen` | `interviewing` | `offer` | `rejected` | `withdrawn`

### Add Notes

```bash
# Interaction note
uv run python .claude/skills/jobhunt/jobhunt.py add-note \
    --about "position-abc123" \
    --type interaction \
    --content "Phone screen went well, moving to technical round." \
    --interaction-type "call" \
    --interaction-date "2025-02-05"

# Strategy note
uv run python .claude/skills/jobhunt/jobhunt.py add-note \
    --about "position-abc123" \
    --type strategy \
    --content "Lead with distributed systems experience from caching project."

# Claude Code brief (CC agent writes a brief for the next session)
uv run python .claude/skills/jobhunt/jobhunt.py add-note \
    --about "position-abc123" \
    --type cc-brief \
    --content "Next session: prep for technical interview on 2025-02-10. Focus on system design questions."

# Claude Code feedback (CC agent records feedback from completed interaction)
uv run python .claude/skills/jobhunt/jobhunt.py add-note \
    --about "position-abc123" \
    --type cc-feedback \
    --content "User reported phone screen went well. Interviewer asked about distributed caching. Move to next round."
```

**Note types:** `research` | `strategy` | `interview` | `interaction` | `skill-gap` | `fit-analysis` | `general` | `cc-brief` | `cc-feedback`

---

## 7. Analysis

### Skill Gap Analysis

```bash
uv run python .claude/skills/jobhunt/jobhunt.py show-gaps
```

### Learning Plan

```bash
uv run python .claude/skills/jobhunt/jobhunt.py learning-plan
```

### Add Learning Resources

```bash
uv run python .claude/skills/jobhunt/jobhunt.py add-resource \
    --name "Designing Data-Intensive Applications" \
    --type "book" \
    --url "https://dataintensive.net" \
    --hours 30 \
    --skills "distributed-systems" "system-design"
```

### Link Resource to Requirement

```bash
uv run python .claude/skills/jobhunt/jobhunt.py link-resource \
    --resource "<resource-id>" \
    --requirement "<requirement-id>"
```

### Cross-Skill Integration: Link Literature to Learning Plan

```bash
# Search for papers on a skill gap topic
uv run python .claude/skills/scientific-literature/scientific_literature.py search \
    --query "machine learning systems design" \
    --collection "ML Systems Reading List"

# Link collection to skill gap
uv run python .claude/skills/jobhunt/jobhunt.py link-collection \
    --collection "<collection-id>" \
    --skill "machine-learning"

# Link a specific paper to a learning resource
uv run python .claude/skills/jobhunt/jobhunt.py link-paper \
    --resource "<resource-id>" \
    --paper "<paper-id>"

# View updated plan
uv run python .claude/skills/jobhunt/jobhunt.py learning-plan
```

---

## 8. Reporting and Queries

### JSON Output (programmatic)

```bash
# All positions
uv run python .claude/skills/jobhunt/jobhunt.py list-pipeline

# Filter by status or priority
uv run python .claude/skills/jobhunt/jobhunt.py list-pipeline --status "interviewing"
uv run python .claude/skills/jobhunt/jobhunt.py list-pipeline --priority "high"

# All opportunity types
uv run python .claude/skills/jobhunt/jobhunt.py list-opportunities --type all
uv run python .claude/skills/jobhunt/jobhunt.py list-opportunities --type venture
uv run python .claude/skills/jobhunt/jobhunt.py list-opportunities --type engagement --status active

# Detail views
uv run python .claude/skills/jobhunt/jobhunt.py show-position --id "position-abc123"
uv run python .claude/skills/jobhunt/jobhunt.py show-opportunity --id "venture-abc123"
uv run python .claude/skills/jobhunt/jobhunt.py show-company --id "company-xyz"
uv run python .claude/skills/jobhunt/jobhunt.py show-gaps
uv run python .claude/skills/jobhunt/jobhunt.py learning-plan
```

### Markdown Output (for display to users)

```bash
uv run python .claude/skills/jobhunt/jobhunt.py report-pipeline   # Pipeline overview
uv run python .claude/skills/jobhunt/jobhunt.py report-stats      # Stats summary
uv run python .claude/skills/jobhunt/jobhunt.py report-gaps       # Skill gaps
uv run python .claude/skills/jobhunt/jobhunt.py report-position --id "position-xyz"  # Position detail
```

Use reports (Markdown) for displaying to users in chat. Use JSON commands (`list-pipeline`, `show-position`) for programmatic processing.

### Tagging

```bash
uv run python .claude/skills/jobhunt/jobhunt.py tag --entity "position-abc123" --tag "remote"
uv run python .claude/skills/jobhunt/jobhunt.py search-tag --tag "remote"
```

---

## 9. Opportunity Model

The jobhunt skill tracks multiple types of career opportunities via the `jobhunt-opportunity` hierarchy:

```
jobhunt-opportunity (base)
+-- jobhunt-position    -- formal employment application (has application-status pipeline)
+-- jobhunt-engagement  -- paid consulting/service work for a client
+-- jobhunt-venture     -- startup/advisory/equity opportunity
+-- jobhunt-lead        -- early-stage networking contact, role undefined
```

All opportunity types share: `opportunity-status`, `priority-level`, `deadline`, and can be linked to a `jobhunt-company` via `opportunity-at-organization`.

All opportunity types work with `add-note --about <ID>` -- notes attach to any `identifiable-entity`.

### Update Any Opportunity

```bash
uv run python .claude/skills/jobhunt/jobhunt.py update-opportunity \
    --id "venture-abc123" \
    --status active \
    --stage negotiating \
    --priority high
```

### Modeling Guide

| Situation | Entity type | Key attributes |
|-----------|-------------|----------------|
| Own consulting business | `jobhunt-company` | name, description |
| Startup advisory role | `jobhunt-venture` | venture-stage, equity-type |
| Consulting engagement | `jobhunt-engagement` | engagement-type, rate-info |
| Networking contact (no role yet) | `jobhunt-lead` | opportunity-status, description |
| Formal job application | `jobhunt-position` | job-url, application-status pipeline |

**Phylo strategy pattern:** Use an existing `jobhunt-position` as the anchor for all interactions. Add `jobhunt-interaction-note` entries for each meeting. Only create a separate `jobhunt-lead` if a genuinely new thread emerges from those conversations.

---

## 10. Data Model

### Entity Types

| Type | Description |
|------|-------------|
| `your-skill` | Your skills for gap analysis |
| `jobhunt-company` | An employer/client organization |
| `jobhunt-opportunity` | Base type for all opportunities |
| `jobhunt-position` | Formal job posting (sub opportunity) |
| `jobhunt-engagement` | Consulting engagement (sub opportunity) |
| `jobhunt-venture` | Startup/advisory venture (sub opportunity) |
| `jobhunt-lead` | Networking lead (sub opportunity) |
| `jobhunt-learning-resource` | Course, book, tutorial |
| `jobhunt-contact` | Person at a company |
| `jobhunt-search-source` | Company board for forager |
| `jobhunt-candidate` | Discovered posting (forager) |

### Artifact Types

| Type | Description |
|------|-------------|
| `jobhunt-job-description` | Raw HTML/text from job posting URL |
| `jobhunt-resume` | Resume document |
| `jobhunt-cover-letter` | Cover letter |
| `jobhunt-company-page` | Company website snapshot |
| `jobhunt-proposal` | Proposal or pitch deck for engagement/venture |

### Note Types

| Type | Purpose |
|------|---------|
| `jobhunt-application-note` | Status tracking (positions) |
| `jobhunt-research-note` | Company/opportunity research |
| `jobhunt-interview-note` | Interview prep/feedback |
| `jobhunt-strategy-note` | Talking points, approach |
| `jobhunt-skill-gap-note` | Learning needs |
| `jobhunt-fit-analysis-note` | Fit assessment |
| `jobhunt-interaction-note` | Contact logs |
| `jobhunt-cc-brief-note` | Claude Code brief for next session |
| `jobhunt-cc-feedback-note` | Claude Code feedback from completed interaction |

### Relations

- `position-at-company` -- links position to employer
- `opportunity-at-organization` -- links any opportunity type to a company
- `aboutness` -- links notes to any entity (position, company, opportunity)
- `requirement-of` -- links requirements to positions

### Schema File

- **JobHunt Schema:** `local_skills/jobhunt/schema.tql`
- **Core Schema:** `local_resources/typedb/alhazen_notebook.tql`

---

## 11. Command Reference

### jobhunt.py Commands

| Command | Description | Key Args |
|---------|-------------|----------|
| `ingest-job` | Fetch job URL, store raw | `--url` |
| `add-skill` | Add to your skill profile | `--name`, `--level` |
| `list-skills` | Show your skills | |
| `list-artifacts` | List artifacts by status | `--status` |
| `show-artifact` | Get artifact content | `--id` |
| `add-company` | Add company | `--name` |
| `add-position` | Add position manually | `--title` |
| `add-engagement` | Add consulting engagement | `--name`, `--type`, `--rate` |
| `add-venture` | Add startup/advisory venture | `--name`, `--stage`, `--equity-type` |
| `add-lead` | Add networking lead | `--name`, `--status` |
| `update-opportunity` | Update any opportunity status/stage/priority | `--id` |
| `show-opportunity` | Show any opportunity details | `--id` |
| `list-opportunities` | List by type/status | `--type`, `--status`, `--priority` |
| `add-requirement` | Add skill requirement | `--position`, `--skill` |
| `update-status` | Change position application status | `--position`, `--status` |
| `add-note` | Create any note type | `--about`, `--type`, `--content` |
| `add-resource` | Add learning resource | `--name`, `--type` |
| `link-collection` | Link paper collection to skill gap | `--collection`, `--skill` |
| `link-resource` | Link resource to a skill requirement | `--resource`, `--requirement` |
| `link-paper` | Link learning resource to a paper | `--resource`, `--paper` |
| `list-pipeline` | Show position pipeline | `--status`, `--priority` |
| `show-position` | Position details | `--id` |
| `show-company` | Company details | `--id` |
| `show-gaps` | Skill gap analysis | |
| `learning-plan` | Prioritized study list | |
| `tag` | Tag an entity | `--entity`, `--tag` |
| `search-tag` | Find by tag | `--tag` |
| `report-pipeline` | Pipeline overview (Markdown) | |
| `report-stats` | Stats summary (Markdown) | |
| `report-gaps` | Skill gaps report (Markdown) | |
| `report-position` | Position detail (Markdown) | `--id` |

### job_forager.py Commands

| Command | Description | Key Args |
|---------|-------------|----------|
| `add-source` | Add a search source | `--name`, `--platform`, `--token`/`--query` |
| `list-sources` | List search sources | |
| `remove-source` | Remove a source | `--id`, `--token`, or `--name` |
| `suggest-sources` | Profile-driven suggestions | |
| `search-source` | Search one source | `--source` |
| `heartbeat` | Full discovery cycle | `--min-relevance` |
| `list-candidates` | List candidates | `--status`, `--source` |
| `triage` | Review/dismiss candidate | `--id`, `--action` |
| `promote` | Promote to position | `--id` |

---

## 12. Quality Checks

Declarative audit rules for data quality are defined in `quality-checks.yaml`.

### Run Audits

```bash
# Check for violations
uv run python .claude/skills/jobhunt/jobhunt.py audit

# Auto-fix where possible
uv run python .claude/skills/jobhunt/jobhunt.py audit --fix

# Or use the generic audit runner
uv run python src/skillful_alhazen/utils/audit_runner.py run \
    --checks local_skills/jobhunt/quality-checks.yaml
```

### Current Checks

| Check | Severity | Description |
|-------|----------|-------------|
| `position-company-link` | high | Positions should be linked to a company via `position-at-company` |
| `ugly-titles` | medium | Position titles containing job-board boilerplate |
| `missing-short-name` | medium | Positions without a `short-name` for compact display |
| `missing-salary` | low | Positions without `salary-range` information |
| `positions-without-notes` | low | Positions with no notes at all |
| `duplicate-companies` | high | Multiple company entities with identical names |
| `orphaned-companies` | medium | Companies with no positions or opportunities linked |

---

## 13. Dashboard

A Next.js dashboard is available for visualizing your job search pipeline. It runs in Docker (not `npm run dev`).

### Docker Build/Run

```bash
docker compose build --no-cache dashboard
docker compose up -d dashboard
# Dashboard available at http://localhost:3001
```

### Views

- **Pipeline Board** (`/jobhunt`) -- Kanban columns by application status
- **Position Detail** (`/jobhunt/position/{id}`) -- Full position profile: requirements, notes, gap analysis, fit score
- **Collection Detail** (`/jobhunt/collection/{id}`) -- Notes and resources grouped by collection

### Internal Organization (for contributors)

- Pages: `dashboard/src/app/(jobhunt)/jobhunt/`
- Components: `dashboard/src/components/jobhunt/`
- API routes: `dashboard/src/app/api/jobhunt/`
- TypeScript wrapper: `dashboard/src/lib/jobhunt.ts`

---

## 14. Schema Gap Recognition

During sensemaking, if you encounter a concept, relationship, or entity type that has no place in the current TypeDB schema, that is a **schema gap** -- a signal for schema evolution, not a failure.

When you notice a schema gap:
1. Complete as much as possible with the current schema (partial knowledge > none)
2. Immediately file a gap issue:

```bash
uv run python local_resources/skilllog/skill_logger.py file-schema-gap \
  --skill jobhunt \
  --concept "<the concept you tried to represent>" \
  --missing "<which TypeDB entity/relation/attribute is absent>" \
  --suggested "<proposed TypeQL addition, or 'unknown' if unsure>"
```

**Examples of schema gaps:**
- A job posting mentions a work arrangement type that isn't in the schema
- A contact has a relationship type (e.g., "mentor") not modeled in `jobhunt-contact`
- An opportunity has a compensation structure (e.g., revenue share) not covered by existing attributes

Use `--dry-run` first to review the issue before filing it.
