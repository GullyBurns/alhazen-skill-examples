---
name: literature
triggers:
  - "search pubmed"
  - "search openalex"
  - "search biorxiv"
  - "search medrxiv"
  - "find papers about"
  - "look up paper"
  - "fetch paper by doi"
  - "ingest paper"
  - "literature search"
  - "add paper to corpus"
  - "embed papers"
  - "semantic search"
  - "find similar papers"
  - "cluster papers"
  - "thematic clustering"
prerequisites:
  - TypeDB running (make db-start)
  - uv sync --all-extras
  - Qdrant running for semantic commands (make qdrant-start)
  - VOYAGE_API_KEY set for embed/search-semantic/cluster
---

# Literature Skill

Multi-source scientific literature search and ingestion for the Alhazen knowledge graph.

**Supported sources:** PubMed (NCBI), OpenAlex, bioRxiv/medRxiv

## Quick Start

```bash
# Search PubMed and store results in a corpus
uv run python .claude/skills/literature/literature.py search \
    --source pubmed --query "CRISPR off-target effects" \
    --collection "collection-abc123" --max-results 20

# Search OpenAlex (broader coverage, JSON-native)
uv run python .claude/skills/literature/literature.py search \
    --source openalex --query "base editing precision" --max-results 10

# Look up a specific paper by DOI
uv run python .claude/skills/literature/literature.py ingest \
    --doi "10.1038/s41587-020-0700-8"

# Show paper content for sensemaking
uv run python .claude/skills/literature/literature.py show \
    --id "scilit-paper-abc123"

# List papers in a corpus
uv run python .claude/skills/literature/literature.py list \
    --collection "collection-abc123"
```

```bash
# Embed a corpus for semantic search (requires VOYAGE_API_KEY + Qdrant)
VOYAGE_API_KEY=xxx uv run python .claude/skills/literature/literature.py embed \
    --collection "collection-abc123"

# Semantic similarity search
VOYAGE_API_KEY=xxx uv run python .claude/skills/literature/literature.py search-semantic \
    --query "CDK8 kinase module stress response" \
    --collection "collection-abc123" --limit 10

# HDBSCAN clustering (dry-run — Claude names themes from representative titles)
VOYAGE_API_KEY=xxx uv run python .claude/skills/literature/literature.py cluster \
    --collection "collection-abc123" --min-cluster-size 15 --dry-run
```

**Read USAGE.md before executing commands** — it has source-specific options,
API key setup, rate limit notes, semantic search workflow, and clustering guide.
