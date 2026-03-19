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

---

## Sensemaking Protocol

Use this structured protocol when reading artifacts and building the mechanism knowledge graph.
Run it after Phase 2 ingestion is complete.

### Step 1: Orient — run show-disease + show-genes

```bash
uv run python $SCRIPT show-disease --mondo-id MONDO:XXXXXXX
uv run python $SCRIPT show-genes --mondo-id MONDO:XXXXXXX
```

Establish: How many causal genes? Inheritance pattern? Phenotype count? Are there any mechanisms
already entered (re-runs)? Note disease_id for subsequent commands.

### Step 2: Read MONDO record artifact

```bash
uv run python $SCRIPT list-artifacts --disease apt-disease-xxxx
# Find the apt-mondo-record artifact, then:
uv run python $SCRIPT show-artifact --id apt-mondo-record-xxxx
```

Key fields to extract: `name`, `description`, `inheritance`, `xrefs` (OMIM, ORPHA), `synonyms`.
The description often contains pathomechanism clues.

### Step 3: Read phenotype associations artifact

```bash
uv run python $SCRIPT show-artifact --id apt-monarch-assoc-record-xxxx
# (the one named "Phenotype associations: ...")
```

Scan for: high-frequency phenotypes (obligate/very-frequent) that anchor the core mechanism.
Group phenotypes by organ system to identify mechanism clusters.

### Step 4: Read gene associations artifact

```bash
uv run python $SCRIPT show-artifact --id apt-monarch-assoc-record-xxxx
# (the one named "Gene associations: ...")
```

Distinguish causal from correlated genes. For monogenic diseases, identify the primary causal gene.
Note HGNC IDs for literature lookup.

### Step 5: Synthesize mechanism hypotheses

**Prompt template for Claude:**
> "Disease X is caused by variants in gene Y (mechanism type: LoF-total/GoF/etc.).
> The key phenotypes are: [list 3-5 most frequent].
> Based on the gene's known function [from MONDO/Monarch description], propose:
> 1. The primary molecular mechanism (one of: GoF, LoF-partial, LoF-total, dominant-negative,
>    haploinsufficiency, toxic-aggregation, pathway-dysregulation)
> 2. How that mechanism causes the top phenotypes
> 3. What therapeutic strategies are rational"

**Decision criteria:**
- One mechanism per distinct pathophysiological pathway (not per phenotype)
- Split mechanisms only if they have different gene involvement or respond to different strategies
- Merge if the same therapeutic approach addresses both
- Use `LoF-total` for null/frameshift variants in recessive disease
- Use `haploinsufficiency` for dominant disease where one copy is insufficient
- Use `GoF` for dominant disease where the variant creates a toxic new function

**Mechanism level selection:**
- `molecular`: protein misfolding, enzyme deficiency, transcription factor loss
- `cellular`: ER stress, mitochondrial dysfunction, lysosomal storage
- `tissue`: neurodegeneration, hepatocyte dysfunction, cardiomyopathy
- `systemic`: metabolic crisis, immune dysregulation

### Step 6: Add mechanisms + link genes + link phenotypes

```bash
# Add mechanism
uv run python $SCRIPT add-mechanism \
  --disease apt-disease-xxxx \
  --type LoF-total \
  --level molecular \
  --description "..."

# Link causal gene (get gene ID from show-genes output)
uv run python $SCRIPT link-mechanism-gene \
  --mechanism apt-mechanism-xxxx --gene apt-gene-xxxx

# Link key phenotypes (get phenotype IDs from show-phenome output)
uv run python $SCRIPT link-mechanism-phenotype \
  --mechanism apt-mechanism-xxxx --phenotype apt-phenotype-xxxx
```

Link at minimum: the primary causal gene + the top 3-5 obligate/very-frequent phenotypes.

### Step 7: Formulate therapeutic strategies per mechanism

For each mechanism, add a therapeutic strategy:

```bash
uv run python $SCRIPT add-strategy \
  --mechanism apt-mechanism-xxxx \
  --modality enzyme-replacement \
  --rationale "Replace deficient enzyme activity via ERT or gene therapy"
```

**Strategy modality guide:**
- `enzyme-replacement` — for enzyme deficiencies (LoF-total, LoF-partial)
- `gene-therapy` — for any LoF where gene delivery is feasible
- `small-molecule-chaperone` — for misfolding with residual activity (LoF-partial)
- `antisense-oligonucleotide` — for toxic mRNA (dominant-negative, GoF)
- `substrate-reduction` — for toxic substrate accumulation upstream of defective enzyme
- `pathway-activation` — for compensatory pathway upregulation
- `symptomatic` — for phenotype management without addressing root cause

Link known drugs to strategies:

```bash
# Check what drugs were ingested from ChEMBL
uv run python $SCRIPT show-therapeutic-map --mondo-id MONDO:XXXXXXX

# Link drug to mechanism
uv run python $SCRIPT link-drug-mechanism \
  --drug apt-drug-xxxx --mechanism apt-mechanism-xxxx
```

### Step 8: Run show-gaps to find remaining unexplained phenotypes/orphan genes

```bash
uv run python $SCRIPT show-gaps --mondo-id MONDO:XXXXXXX
```

For each orphan gene (causal but not in a mechanism): decide whether to create a new mechanism
or link it to an existing one. For unexplained phenotypes: link to the most plausible mechanism
or create a second mechanism if they represent a distinct pathophysiology.

**Evidence threshold for linking:** Use `moderate` evidence if the gene is known to be involved
in the pathway; use `hypothesized` if it is inferred from phenotypic similarity only.

### Step 9: Add apt-research-gaps-note summarizing open questions

```bash
uv run python $SCRIPT add-note \
  --entity apt-disease-xxxx \
  --type apt-research-gaps-note \
  --content "Open questions: 1. Mechanism for phenotype X not yet explained. 2. Gene Y is causal but pathway unknown. 3. No clinical trials targeting primary mechanism."
```

---

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
- `ingest-clintrials --disease DISEASE_ID` — ClinicalTrials.gov (disease name + MONDO ID filter)
- `ingest-drugs --disease DISEASE_ID` — ChEMBL drug-target (by gene) + indication (by MONDO)
- `ingest-omim --disease DISEASE_ID` — OMIM inheritance text + allelic variants (needs `OMIM_API_KEY`)

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
- `show-gaps --mondo-id MONDO_ID` — Undrugged mechanisms + unexplained phenotypes + orphan genes
- `show-repurposing [--mondo-id MONDO_ID]` — Drugs for mechanism types shared across diseases
- `show-sibling-diseases --mondo-id MONDO_ID` — Diseases sharing mechanism types
- `export-report --mondo-id MONDO_ID [--output FILE]` — Comprehensive Markdown report
- `build-corpus --mondo-id MONDO_ID [--execute] [--link-to-investigation ID]` — epmc-search commands

### Notes and Organization
- `add-note --entity ID --type TYPE --content TEXT`
- `tag --entity ID --tag TAG`
- `search-tag --tag TAG`

---

## External APIs

| API | Usage | Endpoint |
|-----|-------|----------|
| Monarch Initiative v3 | Disease search, phenotypes, genes | `https://api-v3.monarchinitiative.org/v3/api` |
| ClinicalTrials.gov v2 | Clinical trials by disease name + MONDO ID | `https://clinicaltrials.gov/api/v2/studies` |
| ChEMBL | Drug-target (by gene) + disease indication (by MONDO) | `https://www.ebi.ac.uk/chembl/api/data` |
| OMIM | Inheritance text + allelic variants (needs `OMIM_API_KEY`) | `https://api.omim.org/api/entry` |

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
