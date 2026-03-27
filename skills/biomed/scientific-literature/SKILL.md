---
name: scientific-literature
triggers:
  - "search epmc"
  - "search pubmed"
  - "search openalex"
  - "search biorxiv"
  - "search medrxiv"
  - "find papers about"
  - "build a corpus"
  - "search literature"
  - "count papers"
  - "ingest paper"
  - "fetch paper by DOI"
  - "look up paper"
  - "add paper to corpus"
  - "embed papers"
  - "semantic search"
  - "find similar papers"
  - "cluster papers"
  - "thematic clustering"
prerequisites:
  - TypeDB running (install alhazen-core first and run /alhazen-core:init)
  - uv installed
  - Qdrant running for semantic commands (docker run -d -p 6333:6333 qdrant/qdrant)
  - VOYAGE_API_KEY set for embed/search-semantic/cluster
---

# Scientific Literature Skill

Multi-source scientific literature search, ingestion, and analysis.
Sources: Europe PMC, PubMed (NCBI), OpenAlex, bioRxiv/medRxiv.

## Quick Start

> **Path note:** Replace `<skill-path>` with your installation directory
> (e.g. `~/.claude/plugins/cache/scientific-literature/` when installed as a plugin).

```bash
# Count papers before committing (EPMC)
uv run --project <skill-path> python <skill-path>/scientific_literature.py count \
    --query "CRISPR AND gene editing"

# Search EPMC and store results in a corpus
uv run --project <skill-path> python <skill-path>/scientific_literature.py search \
    --source epmc --query "CRISPR AND gene editing" --collection "CRISPR Papers" \
    --max-results 500

# Ingest a single paper by DOI (OpenAlex + PubMed fallback)
uv run --project <skill-path> python <skill-path>/scientific_literature.py ingest \
    --doi "10.1038/s41587-020-0700-8"

# List papers in a corpus
uv run --project <skill-path> python <skill-path>/scientific_literature.py list \
    --collection "collection-abc123"
```

**Read USAGE.md before executing commands** -- full command reference, source-specific options,
query syntax, semantic search workflow, and clustering guide.
