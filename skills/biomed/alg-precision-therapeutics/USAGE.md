# Algorithm for Precision Therapeutics - Full Usage Reference

## Overview

This skill implements Matt Might's Algorithm for Precision Medicine (APM) Phase 2
(Therapeutic Phase) as a systematic knowledge graph investigation.

**Starting point:** A known MONDO disease ID (the diagnosis is already known).
**Goal:** Build a mechanism-of-harm centered knowledge graph and identify therapeutic strategies.

**Methodology:** Domain-modeling curation pattern — 5 phases:
1. **Foraging** — Search for and initialize the disease from MONDO/Monarch
2. **Ingestion** — Pull external data (phenotypes, genes, drugs, trials)
3. **Sensemaking** — Claude analyzes artifacts, builds mechanism claims
4. **Analysis** — Mechanism chains, therapeutic map, research gaps
5. **Reporting** — Disease profile, phenome, therapeutic landscape

---

## Workflow

### Phase 1: Initialize

```bash
SCRIPT=".claude/skills/alg-precision-therapeutics/alg_precision_therapeutics.py"

# Find MONDO ID
uv run python $SCRIPT search-disease --query "NGLY1 deficiency"
# => {"diseases": [{"mondo_id": "MONDO:0800044", "name": "NGLY1 deficiency", ...}]}

# Initialize (creates apt-disease + apt-investigation + MONDO artifact)
uv run python $SCRIPT init-investigation MONDO:0800044
# => {"disease_id": "apt-disease-xxxx", "investigation_id": "apt-investigation-xxxx"}
```

### Phase 2: Ingest External Data

```bash
# Full pipeline (runs all ingest-* steps)
uv run python $SCRIPT ingest-disease --mondo-id MONDO:0800044

# OR step by step:
uv run python $SCRIPT ingest-phenotypes --disease apt-disease-xxxx
uv run python $SCRIPT ingest-genes --disease apt-disease-xxxx
uv run python $SCRIPT ingest-hierarchy --disease apt-disease-xxxx
uv run python $SCRIPT ingest-clintrials --disease apt-disease-xxxx
uv run python $SCRIPT ingest-drugs --disease apt-disease-xxxx
```

### Phase 3: Sensemaking (Claude reads artifacts)

```bash
# List artifacts to read
uv run python $SCRIPT list-artifacts --disease apt-disease-xxxx

# Read specific artifact
uv run python $SCRIPT show-artifact --id apt-artifact-xxxx
```

Claude reads the artifacts and synthesizes:
- What mechanism(s) of harm are implied?
- Which genes are causal vs. associated?
- What is the phenotypic burden?
- What therapeutic strategies are rational?

### Phase 4: Build Mechanism Knowledge Graph

```bash
# Add mechanism of harm (Claude-driven, based on sensemaking)
uv run python $SCRIPT add-mechanism \
  --disease apt-disease-xxxx \
  --type LoF-total \
  --level molecular \
  --description "NGLY1 loss of function prevents deglycosylation of misfolded proteins"

# Link mechanism to causal gene
uv run python $SCRIPT link-mechanism-gene \
  --mechanism apt-mechanism-xxxx \
  --gene apt-gene-xxxx

# Link mechanism to key phenotypes it causes
uv run python $SCRIPT link-mechanism-phenotype \
  --mechanism apt-mechanism-xxxx \
  --phenotype apt-phenotype-xxxx

# Add therapeutic strategy
uv run python $SCRIPT add-strategy \
  --mechanism apt-mechanism-xxxx \
  --modality enzyme-replacement \
  --rationale "Replace NGLY1 enzyme activity via ERT or gene therapy"

# Link drug to strategy
uv run python $SCRIPT link-drug-mechanism \
  --drug apt-drug-xxxx \
  --mechanism apt-mechanism-xxxx
```

### Phase 5: Analysis Views

```bash
# Full disease overview
uv run python $SCRIPT show-disease --mondo-id MONDO:0800044

# Mechanism map with gene/phenotype chains
uv run python $SCRIPT show-mechanisms --mondo-id MONDO:0800044

# Therapeutic landscape per mechanism
uv run python $SCRIPT show-therapeutic-map --mondo-id MONDO:0800044

# Phenotypic spectrum by frequency tier
uv run python $SCRIPT show-phenome --mondo-id MONDO:0800044

# Causal genes with evidence
uv run python $SCRIPT show-genes --mondo-id MONDO:0800044

# Clinical trials
uv run python $SCRIPT show-trials --mondo-id MONDO:0800044

# Build literature corpus
uv run python $SCRIPT build-corpus --mondo-id MONDO:0800044
```

---

## Data Model

### Key Innovation: apt-mechanism as First-Class Entity

Unlike the old APM skill where mechanism-of-harm was a relation attribute,
`apt-mechanism` is a **domain-thing entity** with rich attributes and relations:

```
apt-disease -[apt-disease-has-mechanism]-> apt-mechanism
    apt-mechanism attributes:
        apt-mechanism-type: GoF | LoF-partial | LoF-total | dominant-negative |
                            haploinsufficiency | toxic-aggregation | pathway-dysregulation
        apt-mechanism-level: molecular | cellular | tissue | systemic
        apt-therapeutic-addressability: yes | no | partial
        apt-mechanism-evidence-strength: strong | moderate | weak | hypothesized
        apt-functional-impact: overactivity | underactivity | absence | toxicity

Mechanism chain:
    apt-mechanism -[apt-mechanism-involves-gene]-> apt-gene
    apt-mechanism -[apt-mechanism-involves-protein]-> apt-protein
    apt-mechanism -[apt-mechanism-affects-pathway]-> apt-pathway
    apt-mechanism -[apt-mechanism-causes-phenotype]-> apt-phenotype

Therapeutic chain:
    apt-mechanism <-[apt-strategy-targets-mechanism]- apt-therapeutic-strategy
    apt-therapeutic-strategy -[apt-strategy-implements]-> apt-drug
```

### Entity Types

| Entity | Type | Description |
|--------|------|-------------|
| `apt-investigation` | collection | MONDO-rooted investigation root |
| `apt-disease` | domain-thing | Disease with MONDO/OMIM/ORPHA IDs |
| `apt-gene` | domain-thing | Causal or associated gene |
| `apt-mechanism` | domain-thing | Mechanism of harm (first-class) |
| `apt-therapeutic-strategy` | domain-thing | Rational therapeutic approach |
| `apt-phenotype` | domain-thing | Clinical feature (HPO concept) |
| `apt-pathway` | domain-thing | Biological pathway |
| `apt-protein` | domain-thing | Gene product |
| `apt-drug` | domain-thing | Therapeutic compound |
| `apt-clinical-trial` | domain-thing | Clinical trial |
| `apt-mondo-record` | artifact | Raw MONDO API response |
| `apt-monarch-assoc-record` | artifact | Monarch association data |
| `apt-chembl-record` | artifact | ChEMBL drug data |
| `apt-clintrials-record` | artifact | ClinicalTrials.gov data |
| `apt-mechanism-analysis-note` | note | Claude's mechanism analysis |
| `apt-therapeutic-strategy-note` | note | Claude's therapy rationale |

### Mechanism Types (APM Model)

| Type | Description |
|------|-------------|
| `GoF` | Gain of function — protein does too much |
| `LoF-partial` | Partial loss of function — reduced activity |
| `LoF-total` | Complete loss of function — absent activity |
| `dominant-negative` | Mutant protein inhibits wild-type |
| `haploinsufficiency` | One copy insufficient for normal function |
| `toxic-aggregation` | Toxic protein accumulation |
| `pathway-dysregulation` | Indirect pathway effect |

### Mechanism Levels

| Level | Description |
|-------|-------------|
| `molecular` | Protein/DNA/RNA level |
| `cellular` | Cell biology level |
| `tissue` | Organ/tissue level |
| `systemic` | Whole-organism level |

---

## All Commands

### Disease Discovery
- `search-disease --query TEXT [--limit N]` — Search Monarch for MONDO IDs
- `init-investigation MONDO_ID` — Create investigation + disease entity + MONDO artifact
- `list-investigations` — List all investigations in TypeDB

### Automated Ingestion
- `ingest-disease --mondo-id MONDO_ID` — Full pipeline (calls all ingest-* steps)
- `ingest-phenotypes --disease DISEASE_ID` — Monarch HPO associations
- `ingest-genes --disease DISEASE_ID` — Monarch causal/correlated gene associations
- `ingest-hierarchy --disease DISEASE_ID` — MONDO subclass hierarchy
- `ingest-clintrials --disease DISEASE_ID` — ClinicalTrials.gov
- `ingest-drugs --disease DISEASE_ID` — ChEMBL drug-target associations

### Manual Entity Management
- `add-mechanism --disease ID --type TYPE --level LEVEL --description TEXT`
- `add-gene --symbol SYMBOL [--hgnc-id ID]`
- `add-drug --name NAME [--chembl-id ID] [--modality MOD] [--moa TEXT]`
- `add-strategy --mechanism ID --modality MOD --rationale TEXT`
- `add-phenotype --hpo-id ID --disease ID [--frequency FREQ]`
- `link-mechanism-gene --mechanism ID --gene ID`
- `link-mechanism-phenotype --mechanism ID --phenotype ID`
- `link-drug-mechanism --drug ID --mechanism ID`
- `link-drug-target --drug ID --gene ID [--moa TEXT]`

### Artifact Inspection
- `list-artifacts [--disease DISEASE_ID]` — List artifacts
- `show-artifact --id ARTIFACT_ID` — Get artifact content

### Analysis Views
- `show-disease --mondo-id MONDO_ID` — Full disease overview
- `show-mechanisms --mondo-id MONDO_ID` — Mechanisms with gene/phenotype chains
- `show-therapeutic-map --mondo-id MONDO_ID` — Strategies per mechanism
- `show-phenome --mondo-id MONDO_ID` — Phenotypic spectrum by frequency
- `show-genes --mondo-id MONDO_ID` — Causal genes with evidence
- `show-trials --mondo-id MONDO_ID` — Clinical trials landscape
- `build-corpus --mondo-id MONDO_ID` — Print epmc-search commands

### Notes and Organization
- `add-note --entity ID --type TYPE --content TEXT`
- `tag --entity ID --tag TAG`
- `search-tag --tag TAG`

---

## External APIs

| API | Usage | Endpoint |
|-----|-------|----------|
| Monarch Initiative v3 | Disease search, phenotypes, genes | `https://api-v3.monarchinitiative.org/v3/api` |
| ClinicalTrials.gov v2 | Clinical trials by disease name | `https://clinicaltrials.gov/api/v2/studies` |
| ChEMBL | Drug-target associations by gene | `https://www.ebi.ac.uk/chembl/api/data` |

---

## TypeDB Pitfalls

- **Fetch syntax**: `fetch { "key": $var.attr };` (NOT `fetch $var: attr;`)
- **Delete syntax**: `delete $x;` (NOT `delete $x isa type;`)
- **Relations don't have id**: Cannot `fetch $rel.id` where `$rel` is a relation
- **No non-ASCII in queries**: Use ASCII only, even in comments
- Full reference: `local_resources/typedb/llms.txt`

---

## Relation to APM / Rare-Disease Skills

This skill **unifies and replaces** both:
- **`apm`** (patient-centric APM Phase 1+2) — uses broken TypeDB 2.x syntax
- **`rare-disease`** (disease-centric 360 KG) — working 3.x syntax, but mechanism as relation

Key additions over `rare-disease`:
- `apt-mechanism` as first-class entity (not a relation attribute)
- `apt-therapeutic-strategy` as first-class entity
- Full mechanism chain: gene -> pathway -> phenotype -> drug
- APM mechanism type taxonomy (GoF, LoF-partial, LoF-total, dominant-negative, etc.)
- `add-mechanism`, `add-strategy`, `link-*` manual management commands
