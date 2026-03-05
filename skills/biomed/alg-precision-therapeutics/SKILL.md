---
name: alg-precision-therapeutics
description: Investigate rare disease mechanism of harm and therapeutic strategies from a known MONDO diagnosis
---

# Algorithm for Precision Therapeutics (APT)

Use this skill when the diagnosis is KNOWN and the goal is to understand the
**mechanism of harm** and identify **therapeutic strategies**. Follows Matt Might's
APM Phase 2 (Therapeutic Phase) applied systematically to a MONDO disease ID.

Central innovation: `apt-mechanism` is a **first-class entity** linking
gene -> pathway -> phenotype -> drug, not just a relation attribute.

**Triggers:** "mechanism of harm", "investigate disease X", "MONDO disease",
"therapeutic landscape", "rare disease mechanism", "what can treat X",
"APM analysis", "how does X cause disease", "disease knowledge graph",
"build disease KG", "what genes cause X", "rational therapy design",
"precision therapeutics", "Algorithm for Precision Medicine"

**NOT for:** differential diagnosis, variant pathogenicity, or finding a diagnosis
from symptoms - use clinical tools for those.

## Prerequisites

- TypeDB running: `make db-start`
- Dependencies: `uv sync --all-extras`

## Quick Start

```bash
SCRIPT=".claude/skills/alg-precision-therapeutics/alg_precision_therapeutics.py"

# 1. Search for MONDO ID
uv run python $SCRIPT search-disease --query "NGLY1 deficiency"

# 2. Initialize investigation
uv run python $SCRIPT init-investigation MONDO:0800044

# 3. Ingest all external data
uv run python $SCRIPT ingest-disease --mondo-id MONDO:0800044

# 4. View mechanism map (after Claude adds mechanisms)
uv run python $SCRIPT show-mechanisms --mondo-id MONDO:0800044

# 5. View therapeutic map
uv run python $SCRIPT show-therapeutic-map --mondo-id MONDO:0800044
```

Read `USAGE.md` before executing commands.
