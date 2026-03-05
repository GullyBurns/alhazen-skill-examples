# Literature Skill — Usage Reference

Multi-source scientific literature search and ingestion for the Alhazen knowledge graph.
Reuses the `scilit.tql` schema (no additional schema required).

---

## Commands

### `search` — Search a source and ingest results

```bash
uv run python .claude/skills/literature/literature.py search \
    --source <pubmed|openalex|biorxiv|medrxiv> \
    --query "your query here" \
    [--collection collection-abc123] \
    [--max-results 20]
```

**Options:**
- `--source` (required): `pubmed`, `openalex`, `biorxiv`, `medrxiv`
- `--query` (required): Free-text search query
- `--collection`: Collection ID to add results to (optional)
- `--max-results`: Max results to fetch (default: 20)

**Returns:**
```json
{
  "success": true,
  "source": "pubmed",
  "query": "CRISPR off-target",
  "inserted": 18,
  "skipped": 2,
  "papers": [{"id": "scilit-paper-abc", "title": "...", "status": "inserted"}, ...]
}
```

**Deduplication:** Papers already in the graph (matched by DOI or PMID) are skipped.

---

### `ingest` — Fetch a single paper by DOI

```bash
uv run python .claude/skills/literature/literature.py ingest \
    --doi "10.1038/s41587-020-0700-8" \
    [--collection collection-abc123]
```

Tries OpenAlex first (richer abstract via inverted index), then PubMed as fallback.

---

### `show` — Show paper details for sensemaking

```bash
uv run python .claude/skills/literature/literature.py show --id "scilit-paper-abc123"
```

Returns title, abstract, identifiers, and any notes already stored about this paper.

---

### `list` — List papers

```bash
# All papers in graph
uv run python .claude/skills/literature/literature.py list

# Papers in a specific corpus
uv run python .claude/skills/literature/literature.py list --collection "collection-abc123"
```

---

### `embed` — Generate embeddings and load Qdrant

```bash
VOYAGE_API_KEY=xxx uv run python .claude/skills/literature/literature.py embed \
    --collection collection-abc123 [--reembed]
```

**Prerequisites:** Qdrant running (`make qdrant-start`), `VOYAGE_API_KEY` set.

- Fetches all `scilit-paper` members of the collection from TypeDB
- Checks which paper IDs already exist in Qdrant (skips unless `--reembed`)
- Builds embedding text: `title + "\n\n" + abstract`
- Calls Voyage AI `voyage-3-lite` in batches of 128 (1,024-dim vectors)
- Upserts into the `alhazen_papers` Qdrant collection with `collection_id` in payload

**Returns:**
```json
{"success": true, "embedded": 1250, "skipped": 86, "collection_id": "collection-abc123"}
```

**Cost estimate:** ~$0.012 per 1,000 papers (voyage-3-lite is $0.02/M tokens; avg ~600 tokens/paper)

---

### `search-semantic` — Find similar papers by meaning

```bash
VOYAGE_API_KEY=xxx uv run python .claude/skills/literature/literature.py search-semantic \
    --query "cardiac microRNA energy homeostasis" \
    --collection collection-abc123 --limit 10
```

- Embeds query with `input_type="query"` (Voyage distinguishes query vs document)
- Cosine similarity search in Qdrant filtered to the collection
- Returns ranked papers with similarity scores

**Returns:**
```json
{
  "success": true,
  "query": "cardiac microRNA energy homeostasis",
  "results": [
    {"paper_id": "scilit-paper-abc", "title": "...", "doi": "10.xxx", "year": 2023, "score": 0.891},
    ...
  ]
}
```

---

### `cluster` — HDBSCAN thematic clustering

```bash
# Step 1: dry-run to inspect clusters (Claude names themes from representative titles)
VOYAGE_API_KEY=xxx uv run python .claude/skills/literature/literature.py cluster \
    --collection collection-abc123 --min-cluster-size 15 --dry-run

# Step 2: write theme tags back to TypeDB
VOYAGE_API_KEY=xxx uv run python .claude/skills/literature/literature.py cluster \
    --collection collection-abc123 --min-cluster-size 15 \
    --labels 0:transcription-regulation 1:chromatin-remodeling 2:cell-cycle-control
```

**Algorithm:** HDBSCAN on L2-normalized Voyage embeddings (euclidean metric on unit vectors).
Noise points (label=-1) are unclustered and excluded from output.

**Dry-run output:**
```json
{
  "success": true,
  "total_papers": 1336,
  "clustered": 1198,
  "noise": 138,
  "num_clusters": 24,
  "clusters": [
    {
      "cluster_id": 0,
      "size": 87,
      "representative_papers": [
        {"paper_id": "scilit-paper-abc", "title": "...", "doi": "..."},
        ...
      ]
    },
    ...
  ]
}
```

**Workflow:** Run dry-run → Claude reads representative titles and proposes theme names →
re-run with `--labels 0:theme-a 1:theme-b ...` to write `keyword` tags to TypeDB.

**Tuning `--min-cluster-size`:** Start with 15 for large corpora (>500 papers); use 5-10 for small corpora.

---

## Semantic Search Architecture

```
TypeDB (authoritative graph)     Qdrant (semantic index)
────────────────────────────     ─────────────────────────
scilit-paper                     collection: "alhazen_papers"
  id, name, abstract-text          point id = uuid5(paper_id)
  doi, year, keyword               vector = voyage-3-lite(title+abstract)
   (theme tags written back) ←     payload = {paper_id, collection_ids[], title, doi, year}
```

**Environment variables:**
- `VOYAGE_API_KEY` — from https://dash.voyageai.com/
- `QDRANT_HOST` — Qdrant host (default: localhost)
- `QDRANT_PORT` — Qdrant port (default: 6333)

**Starting Qdrant:**
```bash
make qdrant-start   # docker compose up -d qdrant
make qdrant-stop    # docker compose stop qdrant
```

---

## Source Connector Details

### PubMed (NCBI Entrez)

- **API:** `esearch.fcgi` (get PMIDs) + `efetch.fcgi` (get full XML records)
- **Rate limit:** 3 req/s without key; 10 req/s with `NCBI_API_KEY`
- **API key:** Free from https://www.ncbi.nlm.nih.gov/account/
- **Coverage:** ~36M records, all biomedical literature with structured MeSH
- **Best for:** Precise biomedical queries, MeSH-filtered searches

```bash
NCBI_API_KEY="your-key" uv run python .claude/skills/literature/literature.py \
    search --source pubmed --query "CRISPR AND (liver OR hepatocyte)" --max-results 50
```

### OpenAlex

- **API:** `https://api.openalex.org/works?search=...`
- **Rate limit:** Budget-based ($1/day free with API key; 100 req/s shared)
- **API key:** Free from https://openalex.org/settings/api
- **Coverage:** 240M+ works across all disciplines, preprints included
- **Best for:** Broad interdisciplinary searches, citation network queries

```bash
OPENALEX_API_KEY="your-key" uv run python .claude/skills/literature/literature.py \
    search --source openalex --query "base editing precision genome" --max-results 30
```

**OpenAlex abstract note:** Abstracts are stored as inverted indexes (word → positions).
The skill reconstructs full abstract text automatically.

### bioRxiv / medRxiv

- **API:** `https://api.biorxiv.org/pubs/biorxiv/30d/{cursor}` (date range only)
- **Rate limit:** No official limit; skill uses 0.5s delay
- **Authentication:** None required
- **Coverage:** Biology preprints (bioRxiv), health science preprints (medRxiv)
- **Limitation:** No full-text search — fetches last 30 days, filters client-side by keyword

```bash
uv run python .claude/skills/literature/literature.py \
    search --source biorxiv --query "spatial transcriptomics" --max-results 20
```

---

## Typical Workflow

```bash
# 1. Create a corpus collection (via typedb-notebook)
uv run python .claude/skills/typedb-notebook/typedb_notebook.py insert-collection \
    --name "CRISPR Off-Target Review" \
    --description "Papers on CRISPR off-target effects"
# → {"collection_id": "collection-abc123"}

# 2. Search and ingest from multiple sources
uv run python .claude/skills/literature/literature.py search \
    --source pubmed --query "CRISPR off-target effects" \
    --collection "collection-abc123" --max-results 30

uv run python .claude/skills/literature/literature.py search \
    --source openalex --query "CRISPR off-target guide RNA" \
    --collection "collection-abc123" --max-results 20

# 3. List what was ingested
uv run python .claude/skills/literature/literature.py list \
    --collection "collection-abc123"

# 4. Show a paper for sensemaking (Claude reads and annotates)
uv run python .claude/skills/literature/literature.py show \
    --id "scilit-paper-abc123"

# 5. Add a note (via typedb-notebook)
uv run python .claude/skills/typedb-notebook/typedb_notebook.py insert-note \
    --subject "scilit-paper-abc123" \
    --content "Key finding: off-target rate <0.1% with high-fidelity Cas9 variants" \
    --tags crispr off-target high-fidelity
```

---

## Data Model

Papers are stored as `scilit-paper` entities (sub `domain-thing`) using the `scilit.tql` schema:

| Attribute | Type | Notes |
|-----------|------|-------|
| `id` | string @key | Auto-generated (`scilit-paper-xxxxxxxx`) |
| `name` | string | Paper title |
| `abstract-text` | string | Full abstract |
| `doi` | string | DOI (without https://doi.org/ prefix) |
| `pmid` | string | PubMed ID |
| `pmcid` | string | PubMed Central ID |
| `arxiv-id` | string | arXiv ID |
| `publication-year` | integer | Year of publication |
| `journal-name` | string | Journal or preprint server name |
| `source-uri` | string | Canonical URL for this paper |

---

## External Tool Integration Pattern

This skill demonstrates how to integrate multiple external sources into a single Alhazen skill.
See `skills/domain-modeling/USAGE.md` for the full pattern guide.

| Source integration approach | When to use |
|-----------------------------|-------------|
| Raw HTTP client (this skill) | No MCP server exists; stable REST API |
| MCP tool (via Claude) | MCP server exists — e.g., `cyanheads/pubmed-mcp-server` |
| External lib port | Well-tested open-source client (e.g., `medrxivr`) |
| skills-registry.yaml entry | Source has its own complete Alhazen-compatible skill |

**Known MCP servers (as of 2026):**
- PubMed: `@cyanheads/pubmed-mcp-server` (npm)
- OpenAlex: `openalex-research-mcp` (GitHub: oksure/openalex-research-mcp)
- bioRxiv: none found
