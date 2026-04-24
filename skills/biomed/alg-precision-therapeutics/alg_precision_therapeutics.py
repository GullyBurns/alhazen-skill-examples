#!/usr/bin/env python3
"""
Algorithm for Precision Therapeutics CLI - Mechanism-centered rare disease investigation.

Starting from a known MONDO diagnosis, synthesizes mechanism of harm and therapeutic
strategies from Monarch, ClinicalTrials.gov, ChEMBL, and literature.

Central innovation: apt-mechanism is a first-class entity linking
gene -> pathway -> phenotype -> drug.

This script handles INGESTION and QUERIES. Claude handles SENSEMAKING via SKILL.md.

Usage:
    python alg_precision_therapeutics.py <command> [options]

Commands:
    # Disease Discovery
    search-disease          Search Monarch Initiative for diseases by name
    init-investigation      Initialize investigation from MONDO ID
    list-investigations     List all investigations in TypeDB

    # Automated Ingestion
    ingest-disease          Full pipeline: phenotypes + genes + hierarchy + drugs + trials
    ingest-phenotypes       Ingest HPO phenotype associations from Monarch
    ingest-genes            Ingest causal and correlated gene associations from Monarch
    ingest-hierarchy        Ingest MONDO subclass hierarchy
    ingest-drugs            Ingest drug candidates from ChEMBL (gene-targeted + disease-indicated)
    ingest-clintrials       Ingest clinical trials from ClinicalTrials.gov (name + MONDO ID)
    ingest-omim             Ingest OMIM entry: inheritance, allelic variants (needs OMIM_API_KEY)

    # Manual Entity Management
    add-mechanism           Add a mechanism of harm entity
    add-gene                Add a gene entity
    add-drug                Add a drug entity
    add-strategy            Add a therapeutic strategy entity
    add-phenotype           Add a phenotype entity
    link-mechanism-gene     Link mechanism to gene
    link-mechanism-phenotype Link mechanism to phenotype
    link-drug-mechanism     Link drug to mechanism (via strategy)
    link-drug-target        Link drug to gene target

    # Artifact Inspection
    list-artifacts          List artifacts (optionally filtered by disease)
    show-artifact           Get artifact content for sensemaking

    # Analysis Views
    show-disease            Full disease overview
    show-mechanisms         All mechanisms with gene/pathway/phenotype links
    show-therapeutic-map    Strategies per mechanism with drug evidence
    show-phenome            Phenotypic spectrum by frequency tier
    show-genes              Causal genes with association type/evidence
    show-trials             Clinical trials landscape
    show-gaps               Undrugged mechanisms, unexplained phenotypes, orphan genes
    show-repurposing        Drugs targeting mechanism types shared across diseases
    show-sibling-diseases   Diseases sharing mechanism types with query disease
    export-report           Export comprehensive Markdown report

    # Notes and Organization
    add-note                Create a note about any entity
    tag                     Tag an entity
    search-tag              Search entities by tag

    # Evidence Pipeline (DisMech alignment)
    add-evidence            Add literature evidence (PMID + snippet + classification) for a mechanism
    show-evidence           Show all evidence claims for a mechanism with linked papers
    search-evidence         Semantic search for evidence notes and sections (requires VOYAGE_API_KEY)
    fetch-fulltext          Fetch PDF and embed sections for a paper tagged by MONDO ID
    extract-mechanism-claims Use Claude to auto-extract mechanistic claims from paper sections

    # Scaffold
    build-corpus            Print (or execute) scientific-literature CLI commands (360-view)

Environment:
    TYPEDB_HOST       TypeDB server host (default: localhost)
    TYPEDB_PORT       TypeDB server port (default: 1729)
    TYPEDB_DATABASE   Database name (default: alhazen_notebook)
    TYPEDB_USERNAME   TypeDB username (default: admin)
    TYPEDB_PASSWORD   TypeDB password (default: password)
    ALHAZEN_CACHE_DIR File cache directory (default: ~/.alhazen/cache)
"""

import argparse
import hashlib
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    from typedb.driver import Credentials, DriverOptions, TransactionType, TypeDB
    TYPEDB_AVAILABLE = True
except ImportError:
    TYPEDB_AVAILABLE = False
    print(
        "Warning: typedb-driver not installed. Install with: pip install 'typedb-driver>=3.8.0'",
        file=sys.stderr,
    )

# ---------------------------------------------------------------------------
# Cache utilities (inlined — no external package needed)
# ---------------------------------------------------------------------------

_CACHE_THRESHOLD = 50 * 1024  # 50KB

_MIME_TYPE_MAP = {
    "text/html": ("html", "html"),
    "application/xhtml+xml": ("html", "html"),
    "application/pdf": ("pdf", "pdf"),
    "image/png": ("image", "png"),
    "image/jpeg": ("image", "jpg"),
    "image/gif": ("image", "gif"),
    "image/webp": ("image", "webp"),
    "image/svg+xml": ("image", "svg"),
    "application/json": ("json", "json"),
    "text/plain": ("text", "txt"),
    "text/markdown": ("text", "md"),
    "text/csv": ("text", "csv"),
    "application/xml": ("text", "xml"),
    "text/xml": ("text", "xml"),
}


def _get_cache_dir():
    cache_env = os.getenv("ALHAZEN_CACHE_DIR")
    cache_dir = Path(cache_env).expanduser() if cache_env else Path.home() / ".alhazen" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def should_cache(content):
    if isinstance(content, str):
        content = content.encode("utf-8")
    return len(content) >= _CACHE_THRESHOLD


def save_to_cache(artifact_id, content, mime_type):
    if isinstance(content, str):
        content_bytes = content.encode("utf-8")
    else:
        content_bytes = content
    type_dir, ext = _MIME_TYPE_MAP.get(mime_type, ("other", "bin"))
    cache_dir = _get_cache_dir()
    type_path = cache_dir / type_dir
    type_path.mkdir(parents=True, exist_ok=True)
    filename = f"{artifact_id}.{ext}"
    full_path = type_path / filename
    full_path.write_bytes(content_bytes)
    return {
        "cache_path": f"{type_dir}/{filename}",
        "file_size": len(content_bytes),
        "content_hash": hashlib.sha256(content_bytes).hexdigest(),
        "full_path": str(full_path),
    }


def load_from_cache_text(cache_path, encoding="utf-8"):
    return (_get_cache_dir() / cache_path).read_bytes().decode(encoding)


def get_cache_stats():
    cache_dir = _get_cache_dir()
    stats = {"cache_dir": str(cache_dir), "total_files": 0, "total_size": 0, "by_type": {}}
    if not cache_dir.exists():
        return stats
    for type_dir in cache_dir.iterdir():
        if type_dir.is_dir():
            type_stats = {"count": 0, "size": 0}
            for f in type_dir.iterdir():
                if f.is_file():
                    type_stats["count"] += 1
                    type_stats["size"] += f.stat().st_size
            if type_stats["count"] > 0:
                stats["by_type"][type_dir.name] = type_stats
                stats["total_files"] += type_stats["count"]
                stats["total_size"] += type_stats["size"]
    return stats


def format_size(size_bytes):
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


CACHE_AVAILABLE = True


# =============================================================================
# CONFIGURATION
# =============================================================================

TYPEDB_HOST = os.getenv("TYPEDB_HOST", "localhost")
TYPEDB_PORT = int(os.getenv("TYPEDB_PORT", "1729"))
TYPEDB_DATABASE = os.getenv("TYPEDB_DATABASE", "alhazen_notebook")
TYPEDB_USERNAME = os.getenv("TYPEDB_USERNAME", "admin")
TYPEDB_PASSWORD = os.getenv("TYPEDB_PASSWORD", "password")

MONARCH_BASE_URL = "https://api-v3.monarchinitiative.org/v3/api"
CLINTRIALS_BASE_URL = "https://clinicaltrials.gov/api/v2"
CHEMBL_BASE_URL = "https://www.ebi.ac.uk/chembl/api/data"

VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY", "")

# HP frequency qualifier mapping (HP codes -> string labels)
HPO_FREQUENCY_MAP = {
    "HP:0040280": "obligate",       # 100%
    "HP:0040281": "very-frequent",  # 80-99%
    "HP:0040282": "frequent",       # 30-79%
    "HP:0040283": "occasional",     # 5-29%
    "HP:0040284": "rare",           # 1-4%
    "HP:0040285": "very-rare",      # <1%
}

FREQUENCY_ORDER = ["obligate", "very-frequent", "frequent", "occasional", "rare", "very-rare", "unknown"]

# APM mechanism types
MECHANISM_TYPES = [
    "GoF",                    # Gain of function
    "LoF-partial",            # Partial loss of function
    "LoF-total",              # Complete loss of function
    "dominant-negative",      # Dominant negative
    "haploinsufficiency",     # One copy insufficient
    "toxic-aggregation",      # Toxic protein aggregation
    "pathway-dysregulation",  # Indirect pathway effect
]


# =============================================================================
# UTILITIES
# =============================================================================


def get_driver():
    """Get TypeDB driver connection."""
    return TypeDB.driver(
        f"{TYPEDB_HOST}:{TYPEDB_PORT}",
        Credentials(TYPEDB_USERNAME, TYPEDB_PASSWORD),
        DriverOptions(is_tls_enabled=False),
    )


def generate_id(prefix: str) -> str:
    """Generate a unique ID with prefix."""
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def escape_string(s) -> str:
    """Escape special characters for TypeQL."""
    if s is None:
        return ""
    return str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "")


def get_timestamp() -> str:
    """Get current timestamp for TypeDB."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


# =============================================================================
# NOTE EMBEDDING CLIENT (Qdrant-backed semantic search for APT notes)
# =============================================================================


class NoteEmbeddingClient:
    """Manages embedding of APT notes into the apt-notes Qdrant collection."""

    COLLECTION = "apt-notes"
    VECTOR_DIM = 1024  # voyage-3

    def __init__(self):
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams  # noqa: F401
        except ImportError:
            raise ImportError("qdrant-client not installed. Run: uv sync --all-extras")

        host = os.getenv("QDRANT_HOST", "localhost")
        port = int(os.getenv("QDRANT_PORT", "6333"))
        self.client = QdrantClient(host=host, port=port)
        self._ensure_collection()

    def _ensure_collection(self):
        from qdrant_client.models import Distance, VectorParams
        existing = {c.name for c in self.client.get_collections().collections}
        if self.COLLECTION not in existing:
            self.client.create_collection(
                collection_name=self.COLLECTION,
                vectors_config=VectorParams(size=self.VECTOR_DIM, distance=Distance.COSINE),
            )

    def embed_note(self, note_id: str, content: str, metadata: dict) -> bool:
        """Embed a note and upsert into apt-notes. Returns True on success."""
        if not VOYAGE_API_KEY:
            return False
        try:
            from skillful_alhazen.utils.embeddings import embed_texts
            vector = embed_texts([content], input_type="document")[0]
            point_id = str(uuid.uuid5(uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8"), note_id))
            from qdrant_client.models import PointStruct
            payload = {"note_id": note_id, **metadata}
            self.client.upsert(
                collection_name=self.COLLECTION,
                points=[PointStruct(id=point_id, vector=vector, payload=payload)]
            )
            return True
        except Exception as e:
            print(f"Warning: embedding failed for note {note_id}: {e}", file=sys.stderr)
            return False

    def search(self, query: str, mondo_id: str = None, top_k: int = 10) -> list:
        """Search apt-notes by semantic similarity."""
        if not VOYAGE_API_KEY:
            return []
        try:
            from skillful_alhazen.utils.embeddings import embed_texts
            vector = embed_texts([query], input_type="query")[0]
            query_filter = None
            if mondo_id:
                from qdrant_client.models import FieldCondition, Filter, MatchValue
                query_filter = Filter(
                    must=[FieldCondition(key="mondo_id", match=MatchValue(value=mondo_id))]
                )
            response = self.client.query_points(
                collection_name=self.COLLECTION,
                query=vector,
                query_filter=query_filter,
                limit=top_k,
                with_payload=True,
            )
            return [
                {
                    "note_id": r.payload.get("note_id"),
                    "note_type": r.payload.get("note_type", ""),
                    "mechanism_id": r.payload.get("mechanism_id", ""),
                    "mondo_id": r.payload.get("mondo_id", ""),
                    "support_type": r.payload.get("support_type", ""),
                    "score": round(r.score, 4),
                }
                for r in response.points
            ]
        except Exception as e:
            print(f"Warning: search failed: {e}", file=sys.stderr)
            return []


def monarch_get(endpoint: str, params: dict = None) -> dict:
    """Make a GET request to the Monarch Initiative API."""
    if not REQUESTS_AVAILABLE:
        return {"error": "requests not installed. Run: uv sync --all-extras"}
    url = f"{MONARCH_BASE_URL}{endpoint}"
    headers = {"Accept": "application/json", "User-Agent": "Alhazen-APT/1.0"}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.HTTPError as e:
        return {"error": f"HTTP {e.response.status_code}: {e.response.text[:200]}"}
    except Exception as e:
        return {"error": str(e)}


def get_disease_info(disease_id: str) -> dict | None:
    """Get disease metadata from TypeDB entity ID."""
    with get_driver() as driver:
        with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
            results = list(tx.query(f'''
                match $d isa apt-disease, has id "{escape_string(disease_id)}";
                fetch {{
                    "id": $d.id,
                    "name": $d.name,
                    "mondo_id": $d.apt-mondo-id,
                    "description": $d.description
                }};
            ''').resolve())
    if not results:
        return None
    return results[0]


def get_disease_by_mondo(mondo_id: str) -> dict | None:
    """Get disease entity from TypeDB by MONDO ID."""
    with get_driver() as driver:
        with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
            results = list(tx.query(f'''
                match $d isa apt-disease, has apt-mondo-id "{escape_string(mondo_id)}";
                fetch {{
                    "id": $d.id,
                    "name": $d.name,
                    "mondo_id": $d.apt-mondo-id
                }};
            ''').resolve())
    if not results:
        return None
    return results[0]


def get_mondo_id(disease_id: str) -> str | None:
    """Get MONDO ID from TypeDB disease entity ID."""
    info = get_disease_info(disease_id)
    if not info:
        return None
    return info.get("mondo_id")


def save_artifact(artifact_id: str, artifact_type: str, name: str, content: str,
                  mime_type: str, source_uri: str, extra_attrs: str = "") -> str:
    """Save an artifact to TypeDB, caching large content."""
    timestamp = get_timestamp()
    if CACHE_AVAILABLE and should_cache(content):
        cache_result = save_to_cache(artifact_id=artifact_id, content=content, mime_type=mime_type)
        query = f'''insert $a isa {artifact_type},
            has id "{artifact_id}",
            has name "{escape_string(name)}",
            has cache-path "{cache_result['cache_path']}",
            has mime-type "{mime_type}",
            has file-size {cache_result['file_size']},
            has source-uri "{escape_string(source_uri)}",
            has created-at {timestamp}{extra_attrs};'''
    else:
        safe_content = content[:50000] if len(content) > 50000 else content
        query = f'''insert $a isa {artifact_type},
            has id "{artifact_id}",
            has name "{escape_string(name)}",
            has content "{escape_string(safe_content)}",
            has mime-type "{mime_type}",
            has source-uri "{escape_string(source_uri)}",
            has created-at {timestamp}{extra_attrs};'''
    with get_driver() as driver:
        with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
            tx.query(query).resolve()
            tx.commit()
    return artifact_id


# =============================================================================
# DISEASE DISCOVERY
# =============================================================================


def cmd_search_disease(args):
    """Search Monarch Initiative for diseases by name."""
    if not REQUESTS_AVAILABLE:
        print(json.dumps({"success": False, "error": "requests not installed"}))
        return

    params = {
        "q": args.query,
        "category": "biolink:Disease",
        "limit": args.limit or 10,
    }
    data = monarch_get("/search", params)
    if "error" in data:
        print(json.dumps({"success": False, "error": data["error"]}))
        return

    results = []
    for item in data.get("items", []):
        results.append({
            "mondo_id": item.get("id", ""),
            "name": item.get("name", ""),
            "description": (item.get("description") or "")[:200],
            "matching_text": item.get("matching_text", ""),
        })

    print(json.dumps({"success": True, "count": len(results), "diseases": results}, indent=2))


def cmd_init_investigation(args):
    """Initialize precision therapeutics investigation from MONDO ID."""
    if not REQUESTS_AVAILABLE:
        print(json.dumps({"success": False, "error": "requests not installed"}))
        return

    mondo_id = args.mondo_id
    if not mondo_id.startswith("MONDO:"):
        mondo_id = f"MONDO:{mondo_id}"

    # Check if already in TypeDB (idempotent)
    existing = get_disease_by_mondo(mondo_id)
    if existing:
        print(json.dumps({
            "success": True,
            "disease_id": existing["id"],
            "name": existing["name"],
            "message": "Investigation already initialized",
            "already_exists": True,
        }, indent=2))
        return

    # Fetch from Monarch
    data = monarch_get(f"/entity/{mondo_id}")
    if "error" in data:
        print(json.dumps({"success": False, "error": data["error"]}))
        return

    name = data.get("name") or data.get("full_name") or mondo_id
    description = (data.get("description") or "")[:1000]
    xrefs = data.get("xrefs") or []

    # Parse cross-references
    omim_id = orpha_id = gard_id = doid_id = ncit_id = ""
    for xref in xrefs:
        xref_str = str(xref.get("id", xref) if isinstance(xref, dict) else xref)
        if xref_str.startswith("OMIM:"):
            omim_id = xref_str
        elif xref_str.startswith("Orphanet:") or xref_str.startswith("ORPHA:"):
            orpha_id = xref_str
        elif xref_str.startswith("GARD:"):
            gard_id = xref_str
        elif xref_str.startswith("DOID:"):
            doid_id = xref_str
        elif xref_str.startswith("NCIT:"):
            ncit_id = xref_str

    # Parse inheritance
    inheritance = ""
    inheritance_data = data.get("inheritance") or []
    if inheritance_data and isinstance(inheritance_data, list):
        first = inheritance_data[0]
        inheritance = first.get("label", "") if isinstance(first, dict) else str(first)

    timestamp = get_timestamp()
    disease_id = generate_id("apt-disease")
    investigation_id = generate_id("apt-investigation")
    artifact_id = generate_id("apt-artifact")

    with get_driver() as driver:
        # Insert disease entity
        disease_query = f'''insert $d isa apt-disease,
            has id "{disease_id}",
            has name "{escape_string(name)}",
            has apt-mondo-id "{escape_string(mondo_id)}",
            has created-at {timestamp}'''
        if description:
            disease_query += f', has description "{escape_string(description)}"'
        if omim_id:
            disease_query += f', has apt-omim-id "{escape_string(omim_id)}"'
        if orpha_id:
            disease_query += f', has apt-orpha-id "{escape_string(orpha_id)}"'
        if gard_id:
            disease_query += f', has apt-gard-id "{escape_string(gard_id)}"'
        if doid_id:
            disease_query += f', has apt-doid-id "{escape_string(doid_id)}"'
        if ncit_id:
            disease_query += f', has apt-ncit-id "{escape_string(ncit_id)}"'
        if inheritance:
            disease_query += f', has apt-inheritance-pattern "{escape_string(inheritance)}"'
        disease_query += ";"

        with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
            tx.query(disease_query).resolve()
            tx.commit()

        # Insert investigation collection
        with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
            tx.query(f'''insert $i isa apt-investigation,
                has id "{investigation_id}",
                has name "APT Investigation: {escape_string(name)}",
                has apt-mondo-id "{escape_string(mondo_id)}",
                has apt-investigation-status "active",
                has created-at {timestamp};''').resolve()
            tx.commit()

        # Add disease to investigation via collection-membership
        with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
            tx.query(f'''match
                $d isa apt-disease, has id "{disease_id}";
                $i isa apt-investigation, has id "{investigation_id}";
            insert (collection: $i, member: $d) isa collection-membership;''').resolve()
            tx.commit()

        # Link investigation directly to disease
        with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
            tx.query(f'''match
                $i isa apt-investigation, has id "{investigation_id}";
                $d isa apt-disease, has id "{disease_id}";
            insert (investigation: $i, disease: $d) isa apt-investigation-for-disease;''').resolve()
            tx.commit()

    # Store MONDO record artifact
    raw_json = json.dumps(data, indent=2)
    mondo_extra = f', has apt-mondo-id "{escape_string(mondo_id)}"'
    save_artifact(
        artifact_id=artifact_id,
        artifact_type="apt-mondo-record",
        name=f"MONDO record: {name}",
        content=raw_json,
        mime_type="application/json",
        source_uri=f"{MONARCH_BASE_URL}/entity/{mondo_id}",
        extra_attrs=mondo_extra,
    )

    # Link artifact to disease
    with get_driver() as driver:
        with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
            tx.query(f'''match
                $a isa apt-mondo-record, has id "{artifact_id}";
                $d isa apt-disease, has id "{disease_id}";
            insert (referent: $d, artifact: $a) isa representation;''').resolve()
            tx.commit()

    print(json.dumps({
        "success": True,
        "disease_id": disease_id,
        "investigation_id": investigation_id,
        "artifact_id": artifact_id,
        "name": name,
        "mondo_id": mondo_id,
        "omim_id": omim_id,
        "orpha_id": orpha_id,
        "message": (
            f"Initialized. Next steps:\n"
            f"  ingest-disease --mondo-id {mondo_id}\n"
            f"  # OR step-by-step:\n"
            f"  ingest-phenotypes --disease {disease_id}\n"
            f"  ingest-genes --disease {disease_id}\n"
            f"  ingest-hierarchy --disease {disease_id}\n"
            f"  ingest-drugs --disease {disease_id}\n"
            f"  ingest-clintrials --disease {disease_id}"
        ),
    }, indent=2))


def cmd_list_investigations(args):
    """List all APT investigations in TypeDB."""
    with get_driver() as driver:
        with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
            results = list(tx.query('''
                match $i isa apt-investigation;
                fetch {
                    "id": $i.id,
                    "name": $i.name,
                    "mondo_id": $i.apt-mondo-id,
                    "status": $i.apt-investigation-status,
                    "created_at": $i.created-at
                };
            ''').resolve())

    print(json.dumps({"success": True, "count": len(results), "investigations": results}, indent=2))


# =============================================================================
# AUTOMATED INGESTION
# =============================================================================


def cmd_ingest_disease(args):
    """Full ingestion pipeline for a MONDO disease."""
    mondo_id = args.mondo_id
    if not mondo_id.startswith("MONDO:"):
        mondo_id = f"MONDO:{mondo_id}"

    # Ensure disease is initialized
    existing = get_disease_by_mondo(mondo_id)
    if not existing:
        print(json.dumps({"success": False, "error": f"Disease not initialized. Run: init-investigation {mondo_id}"}))
        return

    disease_id = existing["id"]
    results = {"disease_id": disease_id, "mondo_id": mondo_id, "steps": {}}

    # Run all ingestion steps
    for step, func, step_args in [
        ("phenotypes", cmd_ingest_phenotypes, type("A", (), {"disease": disease_id})()),
        ("genes", cmd_ingest_genes, type("A", (), {"disease": disease_id})()),
        ("hierarchy", cmd_ingest_hierarchy, type("A", (), {"disease": disease_id})()),
        ("clintrials", cmd_ingest_clintrials, type("A", (), {"disease": disease_id})()),
        ("drugs", cmd_ingest_drugs, type("A", (), {"disease": disease_id})()),
    ]:
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            func(step_args)
        try:
            step_result = json.loads(buf.getvalue())
        except json.JSONDecodeError:
            step_result = {"raw": buf.getvalue()[:200]}
        results["steps"][step] = step_result

    results["success"] = True
    results["message"] = f"Full ingestion complete for {mondo_id}. Run: show-mechanisms --mondo-id {mondo_id}"
    print(json.dumps(results, indent=2))


def cmd_ingest_phenotypes(args):
    """Ingest HPO phenotype associations from Monarch Initiative."""
    if not REQUESTS_AVAILABLE:
        print(json.dumps({"success": False, "error": "requests not installed"}))
        return

    mondo_id = get_mondo_id(args.disease)
    if not mondo_id:
        print(json.dumps({"success": False, "error": f"Disease not found: {args.disease}"}))
        return

    disease_info = get_disease_info(args.disease)
    disease_name = disease_info.get("name", mondo_id) if disease_info else mondo_id

    params = {"limit": 500}
    data = monarch_get(f"/entity/{mondo_id}/biolink:DiseaseToPhenotypicFeatureAssociation", params)
    if "error" in data:
        print(json.dumps({"success": False, "error": data["error"]}))
        return

    associations = data.get("items", [])
    timestamp = get_timestamp()
    inserted = skipped = 0

    with get_driver() as driver:
        for assoc in associations:
            hpo_id = assoc.get("object", "")
            hpo_label = assoc.get("object_label") or hpo_id

            if not hpo_id or not hpo_id.startswith("HP:"):
                skipped += 1
                continue

            # Map frequency qualifier
            freq_qualifier = "unknown"
            fq = assoc.get("frequency_qualifier") or ""
            if fq in HPO_FREQUENCY_MAP:
                freq_qualifier = HPO_FREQUENCY_MAP[fq]
            elif fq.startswith("HP:"):
                freq_qualifier = fq
            else:
                pct = assoc.get("has_percentage")
                if pct is not None:
                    try:
                        p = float(pct)
                        if p >= 100:
                            freq_qualifier = "obligate"
                        elif p >= 80:
                            freq_qualifier = "very-frequent"
                        elif p >= 30:
                            freq_qualifier = "frequent"
                        elif p >= 5:
                            freq_qualifier = "occasional"
                        elif p >= 1:
                            freq_qualifier = "rare"
                        else:
                            freq_qualifier = "very-rare"
                    except (ValueError, TypeError):
                        freq_qualifier = "unknown"

            evidence_code = ""
            for ev in (assoc.get("has_evidence") or []):
                evidence_code = ev.get("id", ev) if isinstance(ev, dict) else str(ev)
                break

            # Upsert phenotype entity
            with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
                existing_p = list(tx.query(f'''
                    match $p isa apt-phenotype, has apt-hpo-id "{escape_string(hpo_id)}";
                    fetch {{ "id": $p.id }};
                ''').resolve())

            if existing_p:
                phenotype_id = existing_p[0]["id"]
            else:
                phenotype_id = generate_id("apt-phenotype")
                with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
                    tx.query(f'''insert $p isa apt-phenotype,
                        has id "{phenotype_id}",
                        has name "{escape_string(hpo_label)}",
                        has apt-hpo-id "{escape_string(hpo_id)}",
                        has apt-hpo-label "{escape_string(hpo_label)}",
                        has created-at {timestamp};''').resolve()
                    tx.commit()

            # Check if disease-has-phenotype relation already exists
            with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
                rel_exists = list(tx.query(f'''
                    match
                        $d isa apt-disease, has id "{escape_string(args.disease)}";
                        $p isa apt-phenotype, has id "{phenotype_id}";
                        (disease: $d, phenotype: $p) isa apt-disease-has-phenotype;
                    fetch {{ "disease_id": $d.id }};
                ''').resolve())

            if not rel_exists:
                rel_query = f'''match
                    $d isa apt-disease, has id "{escape_string(args.disease)}";
                    $p isa apt-phenotype, has id "{phenotype_id}";
                insert (disease: $d, phenotype: $p) isa apt-disease-has-phenotype,
                    has apt-frequency-qualifier "{escape_string(freq_qualifier)}"'''
                if evidence_code:
                    rel_query += f', has apt-evidence-code "{escape_string(evidence_code)}"'
                rel_query += ";"
                with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
                    tx.query(rel_query).resolve()
                    tx.commit()
                inserted += 1
            else:
                skipped += 1

    # Store association artifact
    artifact_id = generate_id("apt-artifact")
    save_artifact(
        artifact_id=artifact_id,
        artifact_type="apt-monarch-assoc-record",
        name=f"Phenotype associations: {disease_name}",
        content=json.dumps(data, indent=2),
        mime_type="application/json",
        source_uri=f"{MONARCH_BASE_URL}/entity/{mondo_id}/biolink:DiseaseToPhenotypicFeatureAssociation",
    )

    print(json.dumps({
        "success": True,
        "disease_id": args.disease,
        "mondo_id": mondo_id,
        "total_associations": len(associations),
        "inserted": inserted,
        "skipped_or_updated": skipped,
        "artifact_id": artifact_id,
        "message": f"Ingested {inserted} phenotypes. Run: show-phenome --disease {args.disease}",
    }, indent=2))


def cmd_ingest_genes(args):
    """Ingest causal and correlated gene associations from Monarch Initiative."""
    if not REQUESTS_AVAILABLE:
        print(json.dumps({"success": False, "error": "requests not installed"}))
        return

    mondo_id = get_mondo_id(args.disease)
    if not mondo_id:
        print(json.dumps({"success": False, "error": f"Disease not found: {args.disease}"}))
        return

    disease_info = get_disease_info(args.disease)
    disease_name = disease_info.get("name", mondo_id) if disease_info else mondo_id

    timestamp = get_timestamp()
    causal_inserted = assoc_inserted = skipped = 0
    all_data = {}

    for biolink_cat, rel_type in [
        ("biolink:CausalGeneToDiseaseAssociation", "causal"),
        ("biolink:CorrelatedGeneToDiseaseAssociation", "correlated"),
    ]:
        params = {"limit": 200}
        data = monarch_get(f"/entity/{mondo_id}/{biolink_cat}", params)
        if "error" in data:
            print(json.dumps({"success": False, "error": f"{rel_type}: {data['error']}"}))
            return
        all_data[rel_type] = data

        for assoc in data.get("items", []):
            gene_id_raw = assoc.get("subject", "")
            gene_symbol = assoc.get("subject_label") or gene_id_raw
            gene_name = gene_symbol

            if not gene_id_raw or not (gene_id_raw.startswith("HGNC:") or gene_id_raw.startswith("NCBIGene:")):
                skipped += 1
                continue

            hgnc_id = gene_id_raw if gene_id_raw.startswith("HGNC:") else ""
            entrez_id = gene_id_raw.replace("NCBIGene:", "") if gene_id_raw.startswith("NCBIGene:") else ""

            # Upsert gene entity
            with get_driver() as driver:
                with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
                    if hgnc_id:
                        existing_g = list(tx.query(f'''
                            match $g isa apt-gene, has apt-hgnc-id "{escape_string(hgnc_id)}";
                            fetch {{ "id": $g.id }};
                        ''').resolve())
                    else:
                        existing_g = list(tx.query(f'''
                            match $g isa apt-gene, has apt-gene-symbol "{escape_string(gene_symbol)}";
                            fetch {{ "id": $g.id }};
                        ''').resolve())

            if existing_g:
                gene_entity_id = existing_g[0]["id"]
            else:
                gene_entity_id = generate_id("apt-gene")
                gene_insert = f'''insert $g isa apt-gene,
                    has id "{gene_entity_id}",
                    has name "{escape_string(gene_name)}",
                    has apt-gene-symbol "{escape_string(gene_symbol)}",
                    has created-at {timestamp}'''
                if hgnc_id:
                    gene_insert += f', has apt-hgnc-id "{escape_string(hgnc_id)}"'
                if entrez_id:
                    gene_insert += f', has apt-entrez-id "{escape_string(entrez_id)}"'
                gene_insert += ";"
                with get_driver() as driver:
                    with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
                        tx.query(gene_insert).resolve()
                        tx.commit()

            confidence = assoc.get("score")
            if confidence is not None:
                try:
                    confidence = float(confidence)
                except (ValueError, TypeError):
                    confidence = None

            if rel_type == "causal":
                rel_query = f'''match
                    $g isa apt-gene, has id "{gene_entity_id}";
                    $d isa apt-disease, has id "{escape_string(args.disease)}";
                insert (gene: $g, disease: $d) isa apt-gene-causes-disease'''
                if confidence is not None:
                    rel_query += f", has confidence {confidence}"
                rel_query += ";"
                causal_inserted += 1
            else:
                rel_query = f'''match
                    $g isa apt-gene, has id "{gene_entity_id}";
                    $d isa apt-disease, has id "{escape_string(args.disease)}";
                insert (gene: $g, disease: $d) isa apt-gene-associated-with,
                    has apt-association-type "correlated"'''
                if confidence is not None:
                    rel_query += f", has confidence {confidence}"
                rel_query += ";"
                assoc_inserted += 1

            with get_driver() as driver:
                with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
                    tx.query(rel_query).resolve()
                    tx.commit()

    # Store artifact
    artifact_id = generate_id("apt-artifact")
    save_artifact(
        artifact_id=artifact_id,
        artifact_type="apt-monarch-assoc-record",
        name=f"Gene associations: {disease_name}",
        content=json.dumps(all_data, indent=2),
        mime_type="application/json",
        source_uri=f"{MONARCH_BASE_URL}/entity/{mondo_id}/associations-combined",
    )

    print(json.dumps({
        "success": True,
        "disease_id": args.disease,
        "mondo_id": mondo_id,
        "causal_genes_inserted": causal_inserted,
        "associated_genes_inserted": assoc_inserted,
        "skipped": skipped,
        "artifact_id": artifact_id,
        "message": f"Inserted {causal_inserted} causal + {assoc_inserted} associated genes.",
    }, indent=2))


def cmd_ingest_hierarchy(args):
    """Ingest MONDO disease hierarchy (subclass-of relations) from stored artifact."""
    mondo_id = get_mondo_id(args.disease)
    if not mondo_id:
        print(json.dumps({"success": False, "error": f"Disease not found: {args.disease}"}))
        return

    # Find the stored MONDO record artifact
    with get_driver() as driver:
        with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
            artifacts = list(tx.query(f'''
                match
                    $d isa apt-disease, has id "{escape_string(args.disease)}";
                    (referent: $d, artifact: $a) isa representation;
                    $a isa apt-mondo-record;
                fetch {{
                    "id": $a.id,
                    "content": $a.content,
                    "cache-path": $a.cache-path
                }};
            ''').resolve())

    if not artifacts:
        print(json.dumps({
            "success": False,
            "error": "No MONDO record artifact found. Run init-investigation first.",
        }))
        return

    art = artifacts[0]
    cache_path = art.get("cache-path")
    if cache_path and CACHE_AVAILABLE:
        try:
            content = load_from_cache_text(cache_path)
        except FileNotFoundError:
            content = art.get("content", "")
    else:
        content = art.get("content", "")

    if not content:
        print(json.dumps({"success": False, "error": "Artifact content is empty"}))
        return

    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        print(json.dumps({"success": False, "error": f"JSON parse error: {e}"}))
        return

    super_classes = []
    node_hierarchy = data.get("node_hierarchy", {})
    if isinstance(node_hierarchy, dict):
        super_classes = node_hierarchy.get("super_classes", [])
    if not super_classes:
        for field in ["superClasses", "super_classes", "ancestors"]:
            val = data.get(field, [])
            if val:
                super_classes = val
                break

    timestamp = get_timestamp()
    inserted = skipped = 0

    for sc in super_classes:
        parent_mondo_id = sc.get("id", "") if isinstance(sc, dict) else str(sc)
        parent_name = sc.get("label") or sc.get("name") or parent_mondo_id if isinstance(sc, dict) else parent_mondo_id

        if not parent_mondo_id.startswith("MONDO:"):
            skipped += 1
            continue
        if parent_mondo_id == mondo_id:
            skipped += 1
            continue

        with get_driver() as driver:
            with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
                existing_parent = list(tx.query(f'''
                    match $d isa apt-disease, has apt-mondo-id "{escape_string(parent_mondo_id)}";
                    fetch {{ "id": $d.id }};
                ''').resolve())

        if existing_parent:
            parent_id = existing_parent[0]["id"]
        else:
            parent_id = generate_id("apt-disease")
            with get_driver() as driver:
                with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
                    tx.query(f'''insert $d isa apt-disease,
                        has id "{parent_id}",
                        has name "{escape_string(parent_name)}",
                        has apt-mondo-id "{escape_string(parent_mondo_id)}",
                        has created-at {timestamp};''').resolve()
                    tx.commit()

        with get_driver() as driver:
            with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
                tx.query(f'''match
                    $child isa apt-disease, has id "{escape_string(args.disease)}";
                    $parent isa apt-disease, has id "{parent_id}";
                insert (child-disease: $child, parent-disease: $parent) isa apt-disease-subclass-of;''').resolve()
                tx.commit()
        inserted += 1

    print(json.dumps({
        "success": True,
        "disease_id": args.disease,
        "mondo_id": mondo_id,
        "hierarchy_entries_inserted": inserted,
        "skipped": skipped,
        "message": (
            f"Inserted {inserted} parent disease nodes."
            if inserted else
            "No hierarchy data found in MONDO artifact."
        ),
    }, indent=2))


def cmd_ingest_clintrials(args):
    """Ingest clinical trials from ClinicalTrials.gov."""
    if not REQUESTS_AVAILABLE:
        print(json.dumps({"success": False, "error": "requests not installed"}))
        return

    disease_info = get_disease_info(args.disease)
    if not disease_info:
        print(json.dumps({"success": False, "error": f"Disease not found: {args.disease}"}))
        return

    disease_name = disease_info.get("name", "")
    mondo_id = get_mondo_id(args.disease)

    url = f"{CLINTRIALS_BASE_URL}/studies"
    headers = {"Accept": "application/json", "User-Agent": "Alhazen-APT/1.0"}

    # Collect studies from multiple queries, deduplicate by NCT ID
    all_studies_by_nct = {}
    last_data = {}
    queries_to_run = [{"query.cond": disease_name, "pageSize": 50, "format": "json"}]
    if mondo_id:
        queries_to_run.append({
            "filter.advanced": f"AREA[ConditionSearch]{{{mondo_id}}}",
            "pageSize": 50,
            "format": "json",
        })
    for params in queries_to_run:
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=30)
            resp.raise_for_status()
            q_data = resp.json()
            last_data = q_data
            for study in q_data.get("studies", []):
                nct_id = (study.get("protocolSection", {})
                          .get("identificationModule", {}).get("nctId", ""))
                if nct_id and nct_id not in all_studies_by_nct:
                    all_studies_by_nct[nct_id] = study
        except Exception:
            pass

    if not all_studies_by_nct:
        print(json.dumps({"success": False, "error": "ClinicalTrials API returned no results"}))
        return

    studies = list(all_studies_by_nct.values())
    timestamp = get_timestamp()
    inserted = skipped = 0

    for study in studies:
        protocol = study.get("protocolSection", {})
        ident = protocol.get("identificationModule", {})
        status_mod = protocol.get("statusModule", {})
        design_mod = protocol.get("designModule", {})

        nct_id = ident.get("nctId", "")
        if not nct_id:
            skipped += 1
            continue

        title = ident.get("briefTitle") or ident.get("officialTitle") or nct_id
        trial_status = status_mod.get("overallStatus", "")
        phases = design_mod.get("phases", [])
        trial_phase = phases[0] if phases else "N/A"

        with get_driver() as driver:
            with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
                existing_t = list(tx.query(f'''
                    match $t isa apt-clinical-trial, has apt-nct-id "{escape_string(nct_id)}";
                    fetch {{ "id": $t.id }};
                ''').resolve())

        if existing_t:
            trial_id = existing_t[0]["id"]
        else:
            trial_id = generate_id("apt-trial")
            trial_insert = f'''insert $t isa apt-clinical-trial,
                has id "{trial_id}",
                has name "{escape_string(title[:200])}",
                has apt-nct-id "{escape_string(nct_id)}",
                has apt-trial-status "{escape_string(trial_status)}",
                has apt-trial-phase "{escape_string(trial_phase)}",
                has created-at {timestamp};'''
            with get_driver() as driver:
                with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
                    tx.query(trial_insert).resolve()
                    tx.commit()

        with get_driver() as driver:
            with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
                tx.query(f'''match
                    $t isa apt-clinical-trial, has id "{trial_id}";
                    $d isa apt-disease, has id "{escape_string(args.disease)}";
                insert (trial: $t, disease: $d) isa apt-trial-studies;''').resolve()
                tx.commit()
        inserted += 1

    # Store artifact
    artifact_id = generate_id("apt-artifact")
    save_artifact(
        artifact_id=artifact_id,
        artifact_type="apt-clintrials-record",
        name=f"Clinical trials: {disease_name}",
        content=json.dumps(last_data, indent=2),
        mime_type="application/json",
        source_uri=f"{CLINTRIALS_BASE_URL}/studies?query.cond={disease_name}",
    )

    print(json.dumps({
        "success": True,
        "disease_id": args.disease,
        "total_studies": len(studies),
        "inserted": inserted,
        "skipped": skipped,
        "artifact_id": artifact_id,
        "message": f"Ingested {inserted} clinical trials (searched by name + MONDO ID).",
    }, indent=2))


def cmd_ingest_drugs(args):
    """Ingest drug candidates from ChEMBL for causal genes."""
    if not REQUESTS_AVAILABLE:
        print(json.dumps({"success": False, "error": "requests not installed"}))
        return

    # Get causal genes for this disease
    with get_driver() as driver:
        with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
            genes = list(tx.query(f'''
                match
                    $d isa apt-disease, has id "{escape_string(args.disease)}";
                    (gene: $g, disease: $d) isa apt-gene-causes-disease;
                fetch {{
                    "id": $g.id,
                    "name": $g.name,
                    "symbol": $g.apt-gene-symbol,
                    "hgnc_id": $g.apt-hgnc-id,
                    "entrez_id": $g.apt-entrez-id
                }};
            ''').resolve())

    if not genes:
        print(json.dumps({
            "success": False,
            "error": "No causal genes found. Run ingest-genes first.",
        }))
        return

    timestamp = get_timestamp()
    total_drugs = 0
    all_data = {}

    for gene in genes:
        symbol = gene.get("symbol") or gene.get("name", "")
        if not symbol:
            continue

        # ChEMBL: search for targets by gene symbol
        try:
            resp = requests.get(
                f"{CHEMBL_BASE_URL}/target.json",
                params={"target_synonym__icontains": symbol, "limit": 5},
                headers={"Accept": "application/json"},
                timeout=30,
            )
            resp.raise_for_status()
            target_data = resp.json()
        except Exception as e:
            all_data[symbol] = {"error": str(e)}
            continue

        targets = target_data.get("targets", [])
        all_data[symbol] = {"targets": targets}

        for target in targets[:3]:
            chembl_target_id = target.get("target_chembl_id", "")
            if not chembl_target_id:
                continue

            # Get drugs for this target
            try:
                resp2 = requests.get(
                    f"{CHEMBL_BASE_URL}/activity.json",
                    params={
                        "target_chembl_id": chembl_target_id,
                        "limit": 20,
                        "pchembl_value__isnull": False,
                    },
                    headers={"Accept": "application/json"},
                    timeout=30,
                )
                resp2.raise_for_status()
                activity_data = resp2.json()
            except Exception:
                continue

            for activity in activity_data.get("activities", []):
                mol_id = activity.get("molecule_chembl_id", "")
                mol_name = activity.get("molecule_pref_name") or mol_id
                moa = activity.get("mechanism_of_action") or f"target: {symbol}"

                if not mol_id:
                    continue

                # Upsert drug
                with get_driver() as driver:
                    with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
                        existing_drug = list(tx.query(f'''
                            match $dr isa apt-drug, has apt-chembl-id "{escape_string(mol_id)}";
                            fetch {{ "id": $dr.id }};
                        ''').resolve())

                if existing_drug:
                    drug_id = existing_drug[0]["id"]
                else:
                    drug_id = generate_id("apt-drug")
                    with get_driver() as driver:
                        with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
                            tx.query(f'''insert $dr isa apt-drug,
                                has id "{drug_id}",
                                has name "{escape_string(str(mol_name)[:200])}",
                                has apt-chembl-id "{escape_string(mol_id)}",
                                has apt-mechanism-of-action "{escape_string(str(moa)[:300])}",
                                has apt-development-stage "investigational",
                                has created-at {timestamp};''').resolve()
                            tx.commit()
                    total_drugs += 1

                # Link drug to causal gene
                gene_id = gene.get("id")
                with get_driver() as driver:
                    with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
                        link_exists = list(tx.query(f'''
                            match
                                $dr isa apt-drug, has id "{drug_id}";
                                $g isa apt-gene, has id "{escape_string(gene_id)}";
                                (drug: $dr, target-gene: $g) isa apt-drug-targets;
                            fetch {{ "drug_id": $dr.id }};
                        ''').resolve())

                if not link_exists:
                    with get_driver() as driver:
                        with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
                            tx.query(f'''match
                                $dr isa apt-drug, has id "{drug_id}";
                                $g isa apt-gene, has id "{escape_string(gene_id)}";
                            insert (drug: $dr, target-gene: $g) isa apt-drug-targets,
                                has apt-mechanism-of-action "{escape_string(str(moa)[:300])}",
                                has provenance "ChEMBL";''').resolve()
                            tx.commit()

    # ChEMBL drug indication by disease (MONDO ID -> EFO/MONDO mapping)
    mondo_id = get_mondo_id(args.disease)
    indication_drugs = 0
    if mondo_id:
        # ChEMBL accepts MONDO IDs formatted as "MONDO_XXXXXXX" (underscore)
        efo_id = mondo_id.replace("MONDO:", "MONDO_")
        try:
            resp_ind = requests.get(
                f"{CHEMBL_BASE_URL}/drug_indication.json",
                params={"efo_id": efo_id, "limit": 50},
                headers={"Accept": "application/json"},
                timeout=30,
            )
            resp_ind.raise_for_status()
            indication_data = resp_ind.json()
        except Exception:
            indication_data = {}

        for indication in indication_data.get("drug_indications", []):
            mol_id = indication.get("molecule_chembl_id", "")
            if not mol_id:
                continue

            with get_driver() as driver:
                with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
                    existing_drug = list(tx.query(f'''
                        match $dr isa apt-drug, has apt-chembl-id "{escape_string(mol_id)}";
                        fetch {{ "id": $dr.id }};
                    ''').resolve())

            if existing_drug:
                drug_id = existing_drug[0]["id"]
            else:
                drug_id = generate_id("apt-drug")
                mol_name = indication.get("molecule_name") or mol_id
                with get_driver() as driver:
                    with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
                        tx.query(f'''insert $dr isa apt-drug,
                            has id "{drug_id}",
                            has name "{escape_string(str(mol_name)[:200])}",
                            has apt-chembl-id "{escape_string(mol_id)}",
                            has apt-development-stage "indicated",
                            has created-at {timestamp};''').resolve()
                        tx.commit()
                indication_drugs += 1

            # Link drug to disease via apt-drug-indicated-for
            with get_driver() as driver:
                with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
                    link_exists = list(tx.query(f'''
                        match
                            $dr isa apt-drug, has id "{drug_id}";
                            $d isa apt-disease, has id "{escape_string(args.disease)}";
                            (drug: $dr, indication: $d) isa apt-drug-indicated-for;
                        fetch {{ "drug_id": $dr.id }};
                    ''').resolve())

            if not link_exists:
                with get_driver() as driver:
                    with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
                        tx.query(f'''match
                            $dr isa apt-drug, has id "{drug_id}";
                            $d isa apt-disease, has id "{escape_string(args.disease)}";
                        insert (drug: $dr, indication: $d) isa apt-drug-indicated-for,
                            has provenance "ChEMBL-indication";''').resolve()
                        tx.commit()

    # Store artifact
    artifact_id = generate_id("apt-artifact")
    save_artifact(
        artifact_id=artifact_id,
        artifact_type="apt-chembl-record",
        name=f"ChEMBL drug data: {args.disease}",
        content=json.dumps(all_data, indent=2),
        mime_type="application/json",
        source_uri=f"{CHEMBL_BASE_URL}/",
    )

    print(json.dumps({
        "success": True,
        "disease_id": args.disease,
        "genes_queried": len(genes),
        "drugs_inserted": total_drugs,
        "indication_drugs_inserted": indication_drugs,
        "artifact_id": artifact_id,
        "message": f"Ingested {total_drugs} gene-targeted + {indication_drugs} indicated drugs from ChEMBL.",
    }, indent=2))


# =============================================================================
# MANUAL ENTITY MANAGEMENT
# =============================================================================


def cmd_add_mechanism(args):
    """Add a mechanism of harm entity."""
    timestamp = get_timestamp()
    mechanism_id = generate_id("apt-mechanism")

    with get_driver() as driver:
        with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
            query = f'''insert $m isa apt-mechanism,
                has id "{mechanism_id}",
                has name "{escape_string(args.description[:200])}",
                has apt-mechanism-type "{escape_string(args.type)}",
                has apt-mechanism-level "{escape_string(args.level)}",
                has created-at {timestamp}'''
            if args.description:
                query += f', has description "{escape_string(args.description)}"'
            query += ";"
            tx.query(query).resolve()
            tx.commit()

        # Link to disease
        with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
            tx.query(f'''match
                $m isa apt-mechanism, has id "{mechanism_id}";
                $d isa apt-disease, has id "{escape_string(args.disease)}";
            insert (mechanism: $m, disease: $d) isa apt-disease-has-mechanism;''').resolve()
            tx.commit()

    print(json.dumps({
        "success": True,
        "mechanism_id": mechanism_id,
        "disease_id": args.disease,
        "type": args.type,
        "level": args.level,
        "message": f"Added mechanism {mechanism_id}. Link to gene: link-mechanism-gene --mechanism {mechanism_id} --gene GENE_ID",
    }, indent=2))


def cmd_add_gene(args):
    """Add a gene entity."""
    timestamp = get_timestamp()
    gene_id = generate_id("apt-gene")

    with get_driver() as driver:
        with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
            query = f'''insert $g isa apt-gene,
                has id "{gene_id}",
                has name "{escape_string(args.symbol)}",
                has apt-gene-symbol "{escape_string(args.symbol)}",
                has created-at {timestamp}'''
            if args.hgnc_id:
                query += f', has apt-hgnc-id "{escape_string(args.hgnc_id)}"'
            query += ";"
            tx.query(query).resolve()
            tx.commit()

    print(json.dumps({"success": True, "gene_id": gene_id, "symbol": args.symbol}, indent=2))


def cmd_add_drug(args):
    """Add a drug entity."""
    timestamp = get_timestamp()
    drug_id = generate_id("apt-drug")

    with get_driver() as driver:
        with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
            query = f'''insert $dr isa apt-drug,
                has id "{drug_id}",
                has name "{escape_string(args.name)}",
                has created-at {timestamp}'''
            if args.chembl_id:
                query += f', has apt-chembl-id "{escape_string(args.chembl_id)}"'
            if args.modality:
                query += f', has apt-therapeutic-modality "{escape_string(args.modality)}"'
            if args.moa:
                query += f', has apt-mechanism-of-action "{escape_string(args.moa)}"'
            query += ";"
            tx.query(query).resolve()
            tx.commit()

    print(json.dumps({"success": True, "drug_id": drug_id, "name": args.name}, indent=2))


def cmd_add_strategy(args):
    """Add a therapeutic strategy entity."""
    timestamp = get_timestamp()
    strategy_id = generate_id("apt-strategy")

    with get_driver() as driver:
        with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
            query = f'''insert $s isa apt-therapeutic-strategy,
                has id "{strategy_id}",
                has name "{escape_string(args.rationale[:200])}",
                has apt-therapeutic-approach "{escape_string(args.modality)}",
                has apt-therapeutic-modality "{escape_string(args.modality)}",
                has created-at {timestamp}'''
            if args.rationale:
                query += f', has description "{escape_string(args.rationale)}"'
            query += ";"
            tx.query(query).resolve()
            tx.commit()

        # Link to mechanism
        with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
            tx.query(f'''match
                $s isa apt-therapeutic-strategy, has id "{strategy_id}";
                $m isa apt-mechanism, has id "{escape_string(args.mechanism)}";
            insert (strategy: $s, mechanism: $m) isa apt-strategy-targets-mechanism;''').resolve()
            tx.commit()

    print(json.dumps({
        "success": True,
        "strategy_id": strategy_id,
        "mechanism_id": args.mechanism,
        "message": f"Added strategy. Link to drug: link-drug-mechanism --drug DRUG_ID --mechanism {args.mechanism}",
    }, indent=2))


def cmd_add_phenotype(args):
    """Add a phenotype entity and link to disease."""
    timestamp = get_timestamp()

    # Upsert phenotype
    with get_driver() as driver:
        with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
            existing = list(tx.query(f'''
                match $p isa apt-phenotype, has apt-hpo-id "{escape_string(args.hpo_id)}";
                fetch {{ "id": $p.id }};
            ''').resolve())

    if existing:
        phenotype_id = existing[0]["id"]
    else:
        phenotype_id = generate_id("apt-phenotype")
        with get_driver() as driver:
            with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
                tx.query(f'''insert $p isa apt-phenotype,
                    has id "{phenotype_id}",
                    has name "{escape_string(args.hpo_id)}",
                    has apt-hpo-id "{escape_string(args.hpo_id)}",
                    has created-at {timestamp};''').resolve()
                tx.commit()

    # Link to disease
    with get_driver() as driver:
        with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
            query = f'''match
                $d isa apt-disease, has id "{escape_string(args.disease)}";
                $p isa apt-phenotype, has id "{phenotype_id}";
            insert (disease: $d, phenotype: $p) isa apt-disease-has-phenotype'''
            if args.frequency:
                query += f', has apt-frequency-qualifier "{escape_string(args.frequency)}"'
            query += ";"
            tx.query(query).resolve()
            tx.commit()

    print(json.dumps({"success": True, "phenotype_id": phenotype_id, "hpo_id": args.hpo_id}, indent=2))


def cmd_link_mechanism_gene(args):
    """Link a mechanism to a gene."""
    with get_driver() as driver:
        with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
            tx.query(f'''match
                $m isa apt-mechanism, has id "{escape_string(args.mechanism)}";
                $g isa apt-gene, has id "{escape_string(args.gene)}";
            insert (mechanism: $m, gene: $g) isa apt-mechanism-involves-gene;''').resolve()
            tx.commit()

    print(json.dumps({"success": True, "mechanism_id": args.mechanism, "gene_id": args.gene}, indent=2))


def cmd_link_mechanism_phenotype(args):
    """Link a mechanism to a phenotype (mechanism causes phenotype)."""
    with get_driver() as driver:
        with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
            tx.query(f'''match
                $m isa apt-mechanism, has id "{escape_string(args.mechanism)}";
                $p isa apt-phenotype, has id "{escape_string(args.phenotype)}";
            insert (mechanism: $m, phenotype: $p) isa apt-mechanism-causes-phenotype;''').resolve()
            tx.commit()

    print(json.dumps({"success": True, "mechanism_id": args.mechanism, "phenotype_id": args.phenotype}, indent=2))


def cmd_link_drug_mechanism(args):
    """Link a drug to a mechanism via therapeutic strategy."""
    timestamp = get_timestamp()
    strategy_id = generate_id("apt-strategy")

    with get_driver() as driver:
        with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
            tx.query(f'''insert $s isa apt-therapeutic-strategy,
                has id "{strategy_id}",
                has name "Strategy: drug {args.drug} -> mechanism {args.mechanism}",
                has apt-therapeutic-approach "pharmacological",
                has apt-therapeutic-modality "small-molecule",
                has created-at {timestamp};''').resolve()
            tx.commit()

        with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
            tx.query(f'''match
                $s isa apt-therapeutic-strategy, has id "{strategy_id}";
                $m isa apt-mechanism, has id "{escape_string(args.mechanism)}";
            insert (strategy: $s, mechanism: $m) isa apt-strategy-targets-mechanism;''').resolve()
            tx.commit()

        with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
            tx.query(f'''match
                $s isa apt-therapeutic-strategy, has id "{strategy_id}";
                $dr isa apt-drug, has id "{escape_string(args.drug)}";
            insert (strategy: $s, drug: $dr) isa apt-strategy-implements;''').resolve()
            tx.commit()

    print(json.dumps({
        "success": True,
        "strategy_id": strategy_id,
        "drug_id": args.drug,
        "mechanism_id": args.mechanism,
    }, indent=2))


def cmd_link_drug_target(args):
    """Link a drug to a gene target."""
    with get_driver() as driver:
        with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
            query = f'''match
                $dr isa apt-drug, has id "{escape_string(args.drug)}";
                $g isa apt-gene, has id "{escape_string(args.gene)}";
            insert (drug: $dr, target-gene: $g) isa apt-drug-targets'''
            if args.moa:
                query += f', has apt-mechanism-of-action "{escape_string(args.moa)}"'
            query += ";"
            tx.query(query).resolve()
            tx.commit()

    print(json.dumps({"success": True, "drug_id": args.drug, "gene_id": args.gene}, indent=2))


# =============================================================================
# ARTIFACT INSPECTION
# =============================================================================


def cmd_list_artifacts(args):
    """List artifacts, optionally filtered by disease."""
    with get_driver() as driver:
        with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
            if args.disease:
                results = list(tx.query(f'''
                    match
                        $d isa apt-disease, has id "{escape_string(args.disease)}";
                        (referent: $d, artifact: $a) isa representation;
                    fetch {{
                        "id": $a.id,
                        "name": $a.name,
                        "source_uri": $a.source-uri,
                        "created_at": $a.created-at
                    }};
                ''').resolve())
            else:
                results = list(tx.query('''
                    match $a isa artifact;
                    fetch {
                        "id": $a.id,
                        "name": $a.name,
                        "source_uri": $a.source-uri,
                        "created_at": $a.created-at
                    };
                ''').resolve())

    print(json.dumps({"success": True, "count": len(results), "artifacts": results}, indent=2))


def cmd_show_artifact(args):
    """Get artifact content for sensemaking."""
    with get_driver() as driver:
        with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
            results = list(tx.query(f'''
                match $a isa artifact, has id "{escape_string(args.id)}";
                fetch {{
                    "id": $a.id,
                    "name": $a.name,
                    "content": $a.content,
                    "cache-path": $a.cache-path,
                    "source_uri": $a.source-uri
                }};
            ''').resolve())

    if not results:
        print(json.dumps({"success": False, "error": f"Artifact not found: {args.id}"}))
        return

    art = results[0]
    cache_path = art.get("cache-path")
    if cache_path and CACHE_AVAILABLE:
        try:
            content = load_from_cache_text(cache_path)
            art["content"] = content
        except FileNotFoundError:
            pass

    print(json.dumps({"success": True, "artifact": art}, indent=2))


# =============================================================================
# ANALYSIS VIEWS
# =============================================================================


def cmd_show_disease(args):
    """Full disease overview."""
    mondo_id = args.mondo_id
    if not mondo_id.startswith("MONDO:"):
        mondo_id = f"MONDO:{mondo_id}"

    disease = get_disease_by_mondo(mondo_id)
    if not disease:
        print(json.dumps({"success": False, "error": f"Disease not found: {mondo_id}"}))
        return

    disease_id = disease["id"]

    with get_driver() as driver:
        # Full disease details
        with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
            details = list(tx.query(f'''
                match $d isa apt-disease, has id "{escape_string(disease_id)}";
                fetch {{
                    "id": $d.id,
                    "name": $d.name,
                    "description": $d.description,
                    "mondo_id": $d.apt-mondo-id,
                    "omim_id": $d.apt-omim-id,
                    "orpha_id": $d.apt-orpha-id,
                    "gard_id": $d.apt-gard-id,
                    "inheritance_pattern": $d.apt-inheritance-pattern,
                    "prevalence": $d.apt-prevalence,
                    "age_of_onset": $d.apt-age-of-onset,
                    "created_at": $d.created-at
                }};
            ''').resolve())

        # Mechanism count
        with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
            mechanisms = list(tx.query(f'''
                match
                    $d isa apt-disease, has id "{escape_string(disease_id)}";
                    (disease: $d, mechanism: $m) isa apt-disease-has-mechanism;
                fetch {{
                    "id": $m.id,
                    "name": $m.name,
                    "type": $m.apt-mechanism-type,
                    "level": $m.apt-mechanism-level
                }};
            ''').resolve())

        # Causal genes
        with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
            causal_genes = list(tx.query(f'''
                match
                    $d isa apt-disease, has id "{escape_string(disease_id)}";
                    (gene: $g, disease: $d) isa apt-gene-causes-disease;
                fetch {{
                    "id": $g.id,
                    "symbol": $g.apt-gene-symbol,
                    "hgnc_id": $g.apt-hgnc-id
                }};
            ''').resolve())

        # Phenotype count
        with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
            phenotypes = list(tx.query(f'''
                match
                    $d isa apt-disease, has id "{escape_string(disease_id)}";
                    (disease: $d, phenotype: $p) isa apt-disease-has-phenotype;
                fetch {{ "id": $p.id }};
            ''').resolve())

    result = details[0] if details else {}
    result["mechanisms"] = mechanisms
    result["causal_genes"] = causal_genes
    result["phenotype_count"] = len(phenotypes)

    print(json.dumps({"success": True, "disease": result}, indent=2))


def cmd_show_mechanisms(args):
    """Show all mechanisms with gene/pathway/phenotype links."""
    mondo_id = args.mondo_id
    if not mondo_id.startswith("MONDO:"):
        mondo_id = f"MONDO:{mondo_id}"

    disease = get_disease_by_mondo(mondo_id)
    if not disease:
        print(json.dumps({"success": False, "error": f"Disease not found: {mondo_id}"}))
        return

    disease_id = disease["id"]

    with get_driver() as driver:
        with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
            mechanisms = list(tx.query(f'''
                match
                    $d isa apt-disease, has id "{escape_string(disease_id)}";
                    (disease: $d, mechanism: $m) isa apt-disease-has-mechanism;
                fetch {{
                    "id": $m.id,
                    "name": $m.name,
                    "description": $m.description,
                    "type": $m.apt-mechanism-type,
                    "level": $m.apt-mechanism-level,
                    "functional_impact": $m.apt-functional-impact,
                    "evidence_strength": $m.apt-mechanism-evidence-strength,
                    "therapeutic_addressability": $m.apt-therapeutic-addressability
                }};
            ''').resolve())

        result_mechanisms = []
        for mech in mechanisms:
            mech_id = mech["id"]

            with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
                genes = list(tx.query(f'''
                    match
                        $m isa apt-mechanism, has id "{escape_string(mech_id)}";
                        (mechanism: $m, gene: $g) isa apt-mechanism-involves-gene;
                    fetch {{ "symbol": $g.apt-gene-symbol, "id": $g.id }};
                ''').resolve())

            with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
                phenotypes = list(tx.query(f'''
                    match
                        $m isa apt-mechanism, has id "{escape_string(mech_id)}";
                        (mechanism: $m, phenotype: $p) isa apt-mechanism-causes-phenotype;
                    fetch {{ "hpo_id": $p.apt-hpo-id, "label": $p.apt-hpo-label }};
                ''').resolve())

            with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
                strategies = list(tx.query(f'''
                    match
                        $m isa apt-mechanism, has id "{escape_string(mech_id)}";
                        (mechanism: $m, strategy: $s) isa apt-strategy-targets-mechanism;
                    fetch {{
                        "id": $s.id,
                        "name": $s.name,
                        "approach": $s.apt-therapeutic-approach
                    }};
                ''').resolve())

            mech["genes"] = genes
            mech["phenotypes_caused"] = phenotypes
            mech["therapeutic_strategies"] = strategies
            result_mechanisms.append(mech)

    print(json.dumps({
        "success": True,
        "disease_id": disease_id,
        "mondo_id": mondo_id,
        "mechanism_count": len(result_mechanisms),
        "mechanisms": result_mechanisms,
    }, indent=2))


def cmd_show_therapeutic_map(args):
    """Show therapeutic strategies per mechanism with drug evidence."""
    mondo_id = args.mondo_id
    if not mondo_id.startswith("MONDO:"):
        mondo_id = f"MONDO:{mondo_id}"

    disease = get_disease_by_mondo(mondo_id)
    if not disease:
        print(json.dumps({"success": False, "error": f"Disease not found: {mondo_id}"}))
        return

    disease_id = disease["id"]

    with get_driver() as driver:
        with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
            mechanisms = list(tx.query(f'''
                match
                    $d isa apt-disease, has id "{escape_string(disease_id)}";
                    (disease: $d, mechanism: $m) isa apt-disease-has-mechanism;
                fetch {{
                    "id": $m.id,
                    "name": $m.name,
                    "type": $m.apt-mechanism-type,
                    "addressability": $m.apt-therapeutic-addressability
                }};
            ''').resolve())

        result = []
        for mech in mechanisms:
            mech_id = mech["id"]

            with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
                strategies = list(tx.query(f'''
                    match
                        $m isa apt-mechanism, has id "{escape_string(mech_id)}";
                        (mechanism: $m, strategy: $s) isa apt-strategy-targets-mechanism;
                    fetch {{
                        "id": $s.id,
                        "name": $s.name,
                        "approach": $s.apt-therapeutic-approach,
                        "modality": $s.apt-therapeutic-modality
                    }};
                ''').resolve())

            for strat in strategies:
                strat_id = strat["id"]
                with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
                    drugs = list(tx.query(f'''
                        match
                            $s isa apt-therapeutic-strategy, has id "{escape_string(strat_id)}";
                            (strategy: $s, drug: $dr) isa apt-strategy-implements;
                        fetch {{
                            "id": $dr.id,
                            "name": $dr.name,
                            "chembl_id": $dr.apt-chembl-id,
                            "stage": $dr.apt-development-stage,
                            "moa": $dr.apt-mechanism-of-action
                        }};
                    ''').resolve())
                strat["drugs"] = drugs

            mech["strategies"] = strategies
            result.append(mech)

    print(json.dumps({
        "success": True,
        "disease_id": disease_id,
        "therapeutic_map": result,
    }, indent=2))


def cmd_show_phenome(args):
    """Show phenotypic spectrum by frequency tier."""
    # Support both --disease and --mondo-id
    if hasattr(args, "mondo_id") and args.mondo_id:
        mondo_id = args.mondo_id
        if not mondo_id.startswith("MONDO:"):
            mondo_id = f"MONDO:{mondo_id}"
        disease = get_disease_by_mondo(mondo_id)
        if not disease:
            print(json.dumps({"success": False, "error": f"Disease not found: {mondo_id}"}))
            return
        disease_id = disease["id"]
    else:
        disease_id = args.disease

    with get_driver() as driver:
        with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
            # Fetch with frequency (relations attrs must be bound in match, not fetched as $rel.attr)
            results_with_freq = list(tx.query(f'''
                match
                    $d isa apt-disease, has id "{escape_string(disease_id)}";
                    (disease: $d, phenotype: $p) isa apt-disease-has-phenotype,
                        has apt-frequency-qualifier $freq;
                fetch {{
                    "hpo_id": $p.apt-hpo-id,
                    "label": $p.apt-hpo-label,
                    "frequency": $freq
                }};
            ''').resolve())
            # Also get phenotypes without frequency qualifier
            results_no_freq = list(tx.query(f'''
                match
                    $d isa apt-disease, has id "{escape_string(disease_id)}";
                    (disease: $d, phenotype: $p) isa apt-disease-has-phenotype;
                    not {{ (disease: $d, phenotype: $p) isa apt-disease-has-phenotype,
                        has apt-frequency-qualifier $freq2; }};
                fetch {{
                    "hpo_id": $p.apt-hpo-id,
                    "label": $p.apt-hpo-label
                }};
            ''').resolve())
        results = results_with_freq + [dict(r, frequency="unknown") for r in results_no_freq]

    # Group by frequency
    by_freq = {}
    for item in results:
        freq = item.get("frequency") or "unknown"
        by_freq.setdefault(freq, []).append(item)

    ordered = []
    for f in FREQUENCY_ORDER:
        if f in by_freq:
            ordered.append({"frequency_tier": f, "count": len(by_freq[f]), "phenotypes": by_freq[f]})

    print(json.dumps({
        "success": True,
        "disease_id": disease_id,
        "total_phenotypes": len(results),
        "phenome": ordered,
    }, indent=2))


def cmd_show_genes(args):
    """Show causal genes with association type and evidence."""
    mondo_id = args.mondo_id
    if not mondo_id.startswith("MONDO:"):
        mondo_id = f"MONDO:{mondo_id}"

    disease = get_disease_by_mondo(mondo_id)
    if not disease:
        print(json.dumps({"success": False, "error": f"Disease not found: {mondo_id}"}))
        return

    disease_id = disease["id"]

    with get_driver() as driver:
        with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
            causal = list(tx.query(f'''
                match
                    $d isa apt-disease, has id "{escape_string(disease_id)}";
                    (gene: $g, disease: $d) isa apt-gene-causes-disease;
                fetch {{
                    "id": $g.id,
                    "symbol": $g.apt-gene-symbol,
                    "hgnc_id": $g.apt-hgnc-id
                }};
            ''').resolve())

        with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
            associated = list(tx.query(f'''
                match
                    $d isa apt-disease, has id "{escape_string(disease_id)}";
                    (gene: $g, disease: $d) isa apt-gene-associated-with;
                fetch {{
                    "id": $g.id,
                    "symbol": $g.apt-gene-symbol,
                    "hgnc_id": $g.apt-hgnc-id
                }};
            ''').resolve())

    # Add association_type in Python (can't use literals in TypeQL fetch)
    for g in causal:
        g["association_type"] = "causal"
    for g in associated:
        g["association_type"] = "correlated"

    print(json.dumps({
        "success": True,
        "disease_id": disease_id,
        "causal_genes": causal,
        "associated_genes": associated,
    }, indent=2))


def cmd_show_trials(args):
    """Show clinical trials landscape."""
    mondo_id = args.mondo_id
    if not mondo_id.startswith("MONDO:"):
        mondo_id = f"MONDO:{mondo_id}"

    disease = get_disease_by_mondo(mondo_id)
    if not disease:
        print(json.dumps({"success": False, "error": f"Disease not found: {mondo_id}"}))
        return

    disease_id = disease["id"]

    with get_driver() as driver:
        with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
            trials = list(tx.query(f'''
                match
                    $d isa apt-disease, has id "{escape_string(disease_id)}";
                    (trial: $t, disease: $d) isa apt-trial-studies;
                fetch {{
                    "id": $t.id,
                    "name": $t.name,
                    "nct_id": $t.apt-nct-id,
                    "phase": $t.apt-trial-phase,
                    "status": $t.apt-trial-status
                }};
            ''').resolve())

    # Group by phase
    by_phase = {}
    for t in trials:
        phase = t.get("phase") or "N/A"
        by_phase.setdefault(phase, []).append(t)

    print(json.dumps({
        "success": True,
        "disease_id": disease_id,
        "total_trials": len(trials),
        "by_phase": by_phase,
    }, indent=2))


# =============================================================================
# GAP ANALYSIS COMMANDS
# =============================================================================


def cmd_show_gaps(args):
    """Show undrugged mechanisms, unexplained phenotypes, and orphan causal genes."""
    mondo_id = args.mondo_id
    if not mondo_id.startswith("MONDO:"):
        mondo_id = f"MONDO:{mondo_id}"

    with get_driver() as driver:
        # Undrugged mechanisms (no therapeutic strategy linked)
        with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
            undrugged = list(tx.query(f'''
                match
                    $d isa apt-disease, has apt-mondo-id $mid;
                    $mid == "{escape_string(mondo_id)}";
                    (disease: $d, mechanism: $m) isa apt-disease-has-mechanism;
                    not {{ (mechanism: $m, strategy: $s) isa apt-strategy-targets-mechanism; }};
                fetch {{
                    "id": $m.id, "name": $m.name, "type": $m.apt-mechanism-type
                }};
            ''').resolve())

        # Unexplained phenotypes (not linked to any mechanism)
        with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
            unexplained = list(tx.query(f'''
                match
                    $d isa apt-disease, has apt-mondo-id $mid;
                    $mid == "{escape_string(mondo_id)}";
                    (disease: $d, phenotype: $p) isa apt-disease-has-phenotype;
                    not {{ (mechanism: $m, phenotype: $p) isa apt-mechanism-causes-phenotype; }};
                fetch {{
                    "hpo_id": $p.apt-hpo-id, "label": $p.apt-hpo-label
                }};
            ''').resolve())

        # Orphan causal genes (causal but not in any mechanism)
        with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
            orphan_genes = list(tx.query(f'''
                match
                    $d isa apt-disease, has apt-mondo-id $mid;
                    $mid == "{escape_string(mondo_id)}";
                    (gene: $g, disease: $d) isa apt-gene-causes-disease;
                    not {{ (mechanism: $m, gene: $g) isa apt-mechanism-involves-gene; }};
                fetch {{
                    "symbol": $g.apt-gene-symbol, "name": $g.name
                }};
            ''').resolve())

    print(json.dumps({
        "success": True,
        "mondo_id": mondo_id,
        "undrugged_mechanisms": undrugged,
        "unexplained_phenotypes": unexplained,
        "orphan_genes": orphan_genes,
        "summary": {
            "undrugged_count": len(undrugged),
            "unexplained_phenotype_count": len(unexplained),
            "orphan_gene_count": len(orphan_genes),
        },
    }, indent=2))


def cmd_show_repurposing(args):
    """Find drugs targeting mechanism types shared across multiple diseases."""
    mondo_id = getattr(args, "mondo_id", None)
    if mondo_id and not mondo_id.startswith("MONDO:"):
        mondo_id = f"MONDO:{mondo_id}"

    with get_driver() as driver:
        with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
            if mondo_id:
                results = list(tx.query(f'''
                    match
                        $d1 isa apt-disease, has apt-mondo-id $mid;
                        $mid == "{escape_string(mondo_id)}";
                        $d2 isa apt-disease;
                        $d1 has id $did1;
                        $d2 has id $did2;
                        $did1 != $did2;
                        (disease: $d1, mechanism: $m1) isa apt-disease-has-mechanism;
                        (disease: $d2, mechanism: $m2) isa apt-disease-has-mechanism;
                        $m1 has apt-mechanism-type $mtype;
                        $m2 has apt-mechanism-type $mtype;
                        (mechanism: $m1, strategy: $s) isa apt-strategy-targets-mechanism;
                        (strategy: $s, drug: $drug) isa apt-strategy-implements;
                    fetch {{
                        "query_disease": $d1.name,
                        "sibling_disease": $d2.name,
                        "mechanism_type": $m1.apt-mechanism-type,
                        "drug_name": $drug.name,
                        "drug_id": $drug.id
                    }};
                ''').resolve())
            else:
                results = list(tx.query('''
                    match
                        $d1 isa apt-disease;
                        $d2 isa apt-disease;
                        $d1 has id $did1;
                        $d2 has id $did2;
                        $did1 != $did2;
                        (disease: $d1, mechanism: $m1) isa apt-disease-has-mechanism;
                        (disease: $d2, mechanism: $m2) isa apt-disease-has-mechanism;
                        $m1 has apt-mechanism-type $mtype;
                        $m2 has apt-mechanism-type $mtype;
                        (mechanism: $m1, strategy: $s) isa apt-strategy-targets-mechanism;
                        (strategy: $s, drug: $drug) isa apt-strategy-implements;
                    fetch {
                        "disease": $d1.name,
                        "sibling_disease": $d2.name,
                        "mechanism_type": $m1.apt-mechanism-type,
                        "drug_name": $drug.name,
                        "drug_id": $drug.id
                    };
                ''').resolve())

    print(json.dumps({
        "success": True,
        "count": len(results),
        "repurposing_opportunities": results,
    }, indent=2))


def cmd_show_sibling_diseases(args):
    """Find diseases sharing at least one mechanism type with the query disease."""
    mondo_id = args.mondo_id
    if not mondo_id.startswith("MONDO:"):
        mondo_id = f"MONDO:{mondo_id}"

    with get_driver() as driver:
        with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
            results = list(tx.query(f'''
                match
                    $d1 isa apt-disease, has apt-mondo-id $mid;
                    $mid == "{escape_string(mondo_id)}";
                    $d2 isa apt-disease;
                    $d1 has id $did1;
                    $d2 has id $did2;
                    $did1 != $did2;
                    (disease: $d1, mechanism: $m1) isa apt-disease-has-mechanism;
                    (disease: $d2, mechanism: $m2) isa apt-disease-has-mechanism;
                    $m1 has apt-mechanism-type $mtype;
                    $m2 has apt-mechanism-type $mtype;
                fetch {{
                    "sibling_disease": $d2.name,
                    "shared_mechanism_type": $m2.apt-mechanism-type
                }};
            ''').resolve())

    print(json.dumps({
        "success": True,
        "mondo_id": mondo_id,
        "count": len(results),
        "sibling_diseases": results,
    }, indent=2))


def cmd_export_report(args):
    """Export a comprehensive Markdown report for a disease investigation."""
    import io
    from contextlib import redirect_stdout

    mondo_id = args.mondo_id
    if not mondo_id.startswith("MONDO:"):
        mondo_id = f"MONDO:{mondo_id}"

    def capture(func, func_args):
        buf = io.StringIO()
        with redirect_stdout(buf):
            func(func_args)
        try:
            return json.loads(buf.getvalue())
        except json.JSONDecodeError:
            return {"error": buf.getvalue()[:200]}

    disease_data = capture(cmd_show_disease, type("A", (), {"mondo_id": mondo_id})())
    mechanisms_data = capture(cmd_show_mechanisms, type("A", (), {"mondo_id": mondo_id})())
    phenome_data = capture(cmd_show_phenome, type("A", (), {"mondo_id": mondo_id, "disease": ""})())
    genes_data = capture(cmd_show_genes, type("A", (), {"mondo_id": mondo_id})())
    tmap_data = capture(cmd_show_therapeutic_map, type("A", (), {"mondo_id": mondo_id})())
    trials_data = capture(cmd_show_trials, type("A", (), {"mondo_id": mondo_id})())
    gaps_data = capture(cmd_show_gaps, type("A", (), {"mondo_id": mondo_id})())

    disease = disease_data.get("disease", {})
    disease_name = disease.get("name", mondo_id)

    lines = [
        f"# {disease_name} -- Precision Therapeutics Report",
        "",
        f"**MONDO ID:** {mondo_id}",
        f"**OMIM:** {disease.get('omim_id', 'N/A')}",
        f"**ORPHA:** {disease.get('orpha_id', 'N/A')}",
        f"**Inheritance:** {disease.get('inheritance_pattern', 'N/A')}",
        "",
        "## Disease Overview",
        "",
        disease.get("description") or "_No description available._",
        "",
        "## Causal Genes",
        "",
    ]

    for g in genes_data.get("causal_genes", []):
        symbol = g.get("symbol") or g.get("id", "unknown")
        hgnc = g.get("hgnc_id", "")
        lines.append(f"- **{symbol}**" + (f" ({hgnc})" if hgnc else ""))

    lines += ["", "## Mechanisms of Harm", ""]
    for m in mechanisms_data.get("mechanisms", []):
        lines.append(f"### {m.get('name') or m.get('id', 'unknown')}")
        lines.append(f"- **Type:** {m.get('type', 'N/A')}")
        lines.append(f"- **Level:** {m.get('level', 'N/A')}")
        if m.get("description"):
            lines.append(f"- **Description:** {m['description']}")
        genes = m.get("genes", [])
        if genes:
            syms = ", ".join(g.get("symbol") or g.get("id", "?") for g in genes)
            lines.append(f"- **Genes:** {syms}")
        phenos = m.get("phenotypes_caused", [])
        if phenos:
            labels = [p.get("label") or p.get("hpo_id", "?") for p in phenos[:5]]
            lines.append(f"- **Phenotypes caused:** {', '.join(labels)}")
        lines.append("")

    lines += ["## Phenotypic Spectrum", ""]
    for tier in phenome_data.get("phenome", []):
        freq = tier.get("frequency_tier", "unknown")
        count = tier.get("count", 0)
        lines.append(f"**{freq}** ({count} phenotypes)")
        for p in tier.get("phenotypes", [])[:5]:
            label = p.get("label") or p.get("hpo_id", "?")
            hpo = p.get("hpo_id", "")
            lines.append(f"  - {label} ({hpo})")
    lines.append("")

    lines += ["## Therapeutic Landscape", ""]
    for m in tmap_data.get("therapeutic_map", []):
        for s in m.get("strategies", []):
            lines.append(f"### {s.get('name') or s.get('id', '?')}")
            lines.append(f"- **Approach:** {s.get('approach', 'N/A')}")
            lines.append(f"- **Modality:** {s.get('modality', 'N/A')}")
            drugs = s.get("drugs", [])
            if drugs:
                drug_names = ", ".join(d.get("name") or d.get("id", "?") for d in drugs[:5])
                lines.append(f"- **Drugs:** {drug_names}")
            lines.append("")

    lines += ["## Clinical Trials", ""]
    total_trials = trials_data.get("total_trials", 0)
    lines.append(f"Total: {total_trials} trials")
    for phase, trial_list in trials_data.get("by_phase", {}).items():
        lines.append(f"\n**Phase {phase}** ({len(trial_list)} trials)")
        for t in trial_list[:3]:
            nct = t.get("nct_id", "")
            name = t.get("name", nct)
            lines.append(f"  - {name[:80]} [{nct}]")
    lines.append("")

    gaps_summary = gaps_data.get("summary", {})
    lines += [
        "## Research Gaps",
        "",
        f"- Undrugged mechanisms: {gaps_summary.get('undrugged_count', 0)}",
        f"- Unexplained phenotypes: {gaps_summary.get('unexplained_phenotype_count', 0)}",
        f"- Orphan causal genes: {gaps_summary.get('orphan_gene_count', 0)}",
        "",
    ]
    for m in gaps_data.get("undrugged_mechanisms", []):
        lines.append(f"**Undrugged mechanism:** {m.get('name') or m.get('id', '?')} ({m.get('type', 'N/A')})")
    for p in gaps_data.get("unexplained_phenotypes", [])[:10]:
        lines.append(f"- Unexplained phenotype: {p.get('label') or p.get('hpo_id', '?')}")
    for g in gaps_data.get("orphan_genes", []):
        lines.append(f"- Orphan gene: {g.get('symbol') or g.get('name', '?')}")

    report = "\n".join(lines)

    if getattr(args, "output", None):
        with open(args.output, "w") as f:
            f.write(report)
        print(json.dumps({
            "success": True,
            "file": args.output,
            "sections": ["overview", "genes", "mechanisms", "phenome", "therapeutic-landscape", "trials", "gaps"],
        }, indent=2))
    else:
        print(report)


# =============================================================================
# OMIM INGESTION
# =============================================================================


def cmd_ingest_omim(args):
    """Ingest OMIM entry: inheritance text, allelic variants. Requires OMIM_API_KEY."""
    omim_api_key = os.getenv("OMIM_API_KEY", "")
    if not omim_api_key:
        print(json.dumps({
            "success": False,
            "error": "OMIM_API_KEY not set. Get a free academic key at https://omim.org/api",
        }))
        return

    if not REQUESTS_AVAILABLE:
        print(json.dumps({"success": False, "error": "requests not installed"}))
        return

    # Get OMIM ID from disease entity
    with get_driver() as driver:
        with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
            results = list(tx.query(f'''
                match $d isa apt-disease, has id "{escape_string(args.disease)}";
                fetch {{
                    "id": $d.id,
                    "name": $d.name,
                    "omim_id": $d.apt-omim-id
                }};
            ''').resolve())

    if not results:
        print(json.dumps({"success": False, "error": f"Disease not found: {args.disease}"}))
        return

    disease_info = results[0]
    omim_id = disease_info.get("omim_id") or ""
    if not omim_id:
        print(json.dumps({
            "success": False,
            "error": f"No OMIM ID for disease {args.disease}. Run init-investigation first.",
        }))
        return

    mim_number = omim_id.replace("OMIM:", "").strip()
    disease_name = disease_info.get("name", args.disease)

    try:
        resp = requests.get(
            "https://api.omim.org/api/entry",
            params={
                "mimNumber": mim_number,
                "include": "text,allelicVariantList",
                "format": "json",
                "apiKey": omim_api_key,
            },
            headers={"Accept": "application/json"},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))
        return

    # Store OMIM record artifact
    artifact_id = generate_id("apt-artifact")
    save_artifact(
        artifact_id=artifact_id,
        artifact_type="apt-omim-record",
        name=f"OMIM record: {disease_name}",
        content=json.dumps(data, indent=2),
        mime_type="application/json",
        source_uri=f"https://api.omim.org/api/entry?mimNumber={mim_number}",
        extra_attrs=f', has apt-omim-id "{escape_string(omim_id)}"',
    )

    # Link artifact to disease
    with get_driver() as driver:
        with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
            tx.query(f'''match
                $a isa apt-omim-record, has id "{artifact_id}";
                $d isa apt-disease, has id "{escape_string(args.disease)}";
            insert (referent: $d, artifact: $a) isa representation;''').resolve()
            tx.commit()

    timestamp = get_timestamp()
    inheritance_updated = False
    variants_inserted = 0

    for entry_wrapper in data.get("omim", {}).get("entryList", []):
        entry_data = entry_wrapper.get("entry", {})

        # Extract inheritance from text sections
        for section_wrapper in entry_data.get("textSectionList", []):
            ts = section_wrapper.get("textSection", {})
            if ts.get("textSectionName") == "inheritance":
                inheritance_text = (ts.get("textSectionContent") or "")[:200]
                if inheritance_text and not inheritance_updated:
                    with get_driver() as driver:
                        with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
                            tx.query(f'''match
                                $d isa apt-disease, has id "{escape_string(args.disease)}";
                            insert $d has apt-inheritance-pattern "{escape_string(inheritance_text)}";
                            ''').resolve()
                            tx.commit()
                    inheritance_updated = True

        # Extract allelic variants
        for av_wrapper in entry_data.get("allelicVariantList", [])[:20]:
            av = av_wrapper.get("allelicVariant", {})
            av_name = av.get("name", "")
            if not av_name:
                continue
            variant_id = generate_id("apt-variant")
            dbsnp_ids = av.get("dbSnpIds") or []
            clinvar_id = dbsnp_ids[0] if dbsnp_ids else ""
            variant_insert = f'''insert $v isa apt-variant,
                has id "{variant_id}",
                has name "{escape_string(av_name[:200])}",
                has created-at {timestamp}'''
            if clinvar_id:
                variant_insert += f', has apt-clinvar-id "{escape_string(clinvar_id)}"'
            variant_insert += ";"
            with get_driver() as driver:
                with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
                    tx.query(variant_insert).resolve()
                    tx.commit()
            variants_inserted += 1

    print(json.dumps({
        "success": True,
        "disease_id": args.disease,
        "omim_id": omim_id,
        "artifact_id": artifact_id,
        "inheritance_updated": inheritance_updated,
        "variants_inserted": variants_inserted,
        "message": f"OMIM data ingested. {variants_inserted} allelic variants added.",
    }, indent=2))


# =============================================================================
# NOTES AND ORGANIZATION
# =============================================================================


def cmd_add_note(args):
    """Create a note about any entity."""
    timestamp = get_timestamp()
    note_id = generate_id("apt-note")
    note_type = args.type or "apt-disease-overview-note"

    with get_driver() as driver:
        with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
            tx.query(f'''insert $n isa {note_type},
                has id "{note_id}",
                has name "Note: {escape_string(args.content[:80])}",
                has content "{escape_string(args.content)}",
                has created-at {timestamp};''').resolve()
            tx.commit()

        # Link note to entity
        with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
            tx.query(f'''match
                $n isa note, has id "{note_id}";
                $e isa identifiable-entity, has id "{escape_string(args.entity)}";
            insert (note: $n, subject: $e) isa aboutness;''').resolve()
            tx.commit()

    print(json.dumps({"success": True, "note_id": note_id, "entity_id": args.entity}, indent=2))


def cmd_tag(args):
    """Tag an entity."""
    with get_driver() as driver:
        with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
            tx.query(f'''match
                $e isa identifiable-entity, has id "{escape_string(args.entity)}";
            insert $e has tag "{escape_string(args.tag)}";''').resolve()
            tx.commit()

    print(json.dumps({"success": True, "entity_id": args.entity, "tag": args.tag}, indent=2))


def cmd_search_tag(args):
    """Search entities by tag."""
    with get_driver() as driver:
        with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
            results = list(tx.query(f'''
                match $e isa identifiable-entity, has id $eid, has tag "{escape_string(args.tag)}";
                fetch {{ "id": $e.id, "name": $e.name }};
            ''').resolve())

    print(json.dumps({"success": True, "count": len(results), "entities": results}, indent=2))


def _fetch_disease_synonyms(mondo_id: str) -> list:
    """Fetch useful synonyms from Monarch Initiative entity endpoint."""
    try:
        data = monarch_get(f"/entity/{mondo_id}")
        exact = data.get("exact_synonym") or []
        related = data.get("related_synonym") or []
        all_syns = exact + related
        short = [s for s in all_syns if s and len(s) < 40]
        long_ = [s for s in all_syns if s and len(s) >= 40]
        return (short + long_)[:4]
    except Exception:
        return []


def _fetch_gene_aliases(gene_symbol: str) -> list:
    """Fetch alias symbols from HGNC REST API."""
    try:
        import requests as _req
        resp = _req.get(
            f"https://rest.genenames.org/fetch/symbol/{gene_symbol}",
            headers={"Accept": "application/json"},
            timeout=10,
        )
        docs = resp.json().get("response", {}).get("docs", [])
        if docs:
            return docs[0].get("alias_symbol", []) + docs[0].get("prev_symbol", [])
    except Exception:
        pass
    return []


def _fetch_top_phenotypes(driver, disease_id: str) -> list:
    """Return phenotype labels for obligate/very-frequent/frequent phenotypes."""
    try:
        with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
            results = list(tx.query(f'''
                match
                    $d isa apt-disease, has id "{escape_string(disease_id)}";
                    $p isa apt-phenotype, has apt-hpo-label $label;
                    $rel (disease: $d, phenotype: $p) isa apt-disease-has-phenotype,
                        has apt-frequency-qualifier $freq;
                fetch {{ "label": $label, "freq": $freq }};
            ''').resolve())
        high_freq = {"obligate", "very frequent", "frequent",
                     "HP:0040280", "HP:0040281", "HP:0040282"}
        filtered = [r.get("label") for r in results
                    if r.get("freq") in high_freq and r.get("label")]
        if filtered:
            return filtered
        all_labels = [r.get("label") for r in results if r.get("label")]
        return all_labels[:6]
    except Exception:
        return []


# =============================================================================
# EVIDENCE PIPELINE COMMANDS (Phase 3: DisMech alignment)
# =============================================================================


def _find_scilit_script() -> str:
    """Return path to scientific_literature.py CLI script."""
    # Try .claude/skills symlink (local dev)
    this_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(this_dir, "..", "scientific-literature", "scientific_literature.py"),
        os.path.join(this_dir, "..", "..", "..", ".claude", "skills",
                     "scientific-literature", "scientific_literature.py"),
        ".claude/skills/scientific-literature/scientific_literature.py",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return os.path.abspath(c)
    return ".claude/skills/scientific-literature/scientific_literature.py"


def _get_mechanism_info(mechanism_id: str) -> dict | None:
    """Fetch mechanism entity data including linked disease mondo_id."""
    with get_driver() as driver:
        with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
            results = list(tx.query(f'''
                match $m isa apt-mechanism, has id "{escape_string(mechanism_id)}";
                fetch {{
                    "id": $m.id,
                    "name": $m.name,
                    "description": $m.description,
                    "mechanism_type": $m.apt-mechanism-type
                }};
            ''').resolve())
        if not results:
            return None
        info = results[0]

        # Get linked disease for mondo_id
        with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
            dres = list(tx.query(f'''
                match
                    $m isa apt-mechanism, has id "{escape_string(mechanism_id)}";
                    $d isa apt-disease;
                    (mechanism: $m, disease: $d) isa apt-disease-has-mechanism;
                fetch {{ "mondo_id": $d.apt-mondo-id, "disease_id": $d.id }};
            ''').resolve())
        if dres:
            info["mondo_id"] = dres[0].get("mondo_id", "")
            info["disease_id"] = dres[0].get("disease_id", "")
        else:
            info["mondo_id"] = ""
            info["disease_id"] = ""
    return info


def _fetch_paper_by_pmid(pmid: str) -> dict | None:
    """Look up scilit-paper in TypeDB by PMID. Returns None if not found."""
    with get_driver() as driver:
        with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
            results = list(tx.query(f'''
                match $p isa scilit-paper, has pmid "{escape_string(pmid)}";
                fetch {{ "id": $p.id, "name": $p.name }};
            ''').resolve())
    return results[0] if results else None


def _insert_minimal_paper(pmid: str) -> dict:
    """Fetch minimal metadata from EPMC and insert a scilit-paper entity. Returns paper info."""
    import subprocess
    # Try EPMC first for minimal metadata
    title = f"PMID:{pmid}"
    abstract = ""
    if REQUESTS_AVAILABLE:
        try:
            resp = requests.get(
                "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
                params={"query": f"EXT_ID:{pmid} AND SRC:MED", "format": "json",
                        "resultType": "core", "pageSize": 1},
                timeout=15,
                headers={"Accept": "application/json"},
            )
            data = resp.json()
            results = data.get("resultList", {}).get("result", [])
            if results:
                r = results[0]
                title = r.get("title", title)
                abstract = r.get("abstractText", "")
        except Exception as e:
            print(f"Warning: EPMC fetch failed for PMID {pmid}: {e}", file=sys.stderr)

    paper_id = generate_id("scilit-paper")
    timestamp = get_timestamp()
    escaped_title = escape_string(title[:400])
    with get_driver() as driver:
        with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
            q = (f'insert $p isa scilit-paper, has id "{paper_id}",'
                 f' has name "{escaped_title}",'
                 f' has pmid "{escape_string(pmid)}",'
                 f' has created-at {timestamp}')
            if abstract:
                q += f', has abstract-text "{escape_string(abstract[:4000])}"'
            q += ";"
            tx.query(q).resolve()
            tx.commit()

    return {"id": paper_id, "name": title}


def cmd_add_evidence(args):
    """Add literature evidence for a mechanism (PMID + snippet + support classification)."""
    timestamp = get_timestamp()

    # 1. Validate mechanism
    mech_info = _get_mechanism_info(args.mechanism_id)
    if not mech_info:
        print(json.dumps({"success": False,
                          "error": f"Mechanism not found: {args.mechanism_id}"}))
        return

    mechanism_type = mech_info.get("mechanism_type", "unknown")
    mondo_id = mech_info.get("mondo_id", "")

    # 2. Look up or insert scilit-paper by PMID
    paper = _fetch_paper_by_pmid(str(args.pmid))
    if not paper:
        print(f"Paper PMID:{args.pmid} not found in TypeDB — fetching from EPMC...",
              file=sys.stderr)
        paper = _insert_minimal_paper(str(args.pmid))

    paper_id = paper["id"]

    # 3. Create scilit-extraction-note (content only — no apt attrs, scilit schema)
    extract_id = generate_id("scilit-extract")
    snippet_escaped = escape_string(args.snippet)
    explanation = escape_string(getattr(args, "explanation", "") or "")
    extract_content = args.snippet
    if explanation:
        extract_content += f"\n\nExplanation: {args.explanation}"

    with get_driver() as driver:
        with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
            tx.query(f'''insert $n isa scilit-extraction-note,
                has id "{extract_id}",
                has name "Evidence: {escape_string(args.snippet[:60])}",
                has content "{escape_string(extract_content)}",
                has created-at {timestamp};''').resolve()
            tx.commit()

        # Link extraction note to paper
        with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
            tx.query(f'''match
                $n isa scilit-extraction-note, has id "{extract_id}";
                $p isa scilit-paper, has id "{paper_id}";
            insert (note: $n, subject: $p) isa aboutness;''').resolve()
            tx.commit()

    # 4. Create apt-mechanism-claim-note
    claim_id = generate_id("apt-claim-note")
    claim_name = f"Claim: {mechanism_type} - {args.support_type}"
    with get_driver() as driver:
        with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
            tx.query(f'''insert $n isa apt-mechanism-claim-note,
                has id "{claim_id}",
                has name "{escape_string(claim_name)}",
                has content "{snippet_escaped}",
                has apt-mechanism-type "{escape_string(mechanism_type)}",
                has apt-support-type "{escape_string(args.support_type)}",
                has apt-evidence-source "{escape_string(args.evidence_source)}",
                has created-at {timestamp};''').resolve()
            tx.commit()

        # Link claim note to mechanism
        with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
            tx.query(f'''match
                $n isa apt-mechanism-claim-note, has id "{claim_id}";
                $m isa apt-mechanism, has id "{escape_string(args.mechanism_id)}";
            insert (note: $n, subject: $m) isa aboutness;''').resolve()
            tx.commit()

        # 5. Link claim -> extraction via evidence-chain
        with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
            tx.query(f'''match
                $claim isa apt-mechanism-claim-note, has id "{claim_id}";
                $extract isa scilit-extraction-note, has id "{extract_id}";
            insert (claim: $claim, evidence: $extract) isa evidence-chain;''').resolve()
            tx.commit()

    # 6. Optionally embed the claim note
    embedded = False
    if VOYAGE_API_KEY:
        try:
            client = NoteEmbeddingClient()
            embedded = client.embed_note(
                note_id=claim_id,
                content=args.snippet,
                metadata={
                    "note_type": "apt-mechanism-claim-note",
                    "mechanism_id": args.mechanism_id,
                    "mondo_id": mondo_id,
                    "support_type": args.support_type,
                },
            )
        except Exception as e:
            print(f"Warning: Qdrant embedding skipped: {e}", file=sys.stderr)

    print(json.dumps({
        "success": True,
        "claim_note_id": claim_id,
        "extraction_note_id": extract_id,
        "paper_id": paper_id,
        "pmid": str(args.pmid),
        "support_type": args.support_type,
        "evidence_source": args.evidence_source,
        "embedded": embedded,
    }, indent=2))


def cmd_show_evidence(args):
    """Show all evidence claims for a mechanism with linked papers."""
    mechanism_id = args.mechanism_id

    with get_driver() as driver:
        # Fetch all claim notes about the mechanism
        with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
            claim_rows = list(tx.query(f'''
                match
                    $mech isa apt-mechanism, has id "{escape_string(mechanism_id)}";
                    $claim isa apt-mechanism-claim-note;
                    (note: $claim, subject: $mech) isa aboutness;
                    $claim has id $cid, has content $ccontent, has apt-support-type $csup,
                           has apt-evidence-source $csrc;
                fetch {{
                    "claim_id": $cid,
                    "content": $ccontent,
                    "support_type": $csup,
                    "evidence_source": $csrc
                }};
            ''').resolve())

    evidence_items = []
    for claim in claim_rows:
        claim_id = claim.get("claim_id", "")
        snippet = (claim.get("content") or "")[:300]

        # Fetch linked extraction notes via evidence-chain
        extraction_content = ""
        paper_title = ""
        pmid = ""
        paper_id = ""

        with get_driver() as driver:
            with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
                extract_rows = list(tx.query(f'''
                    match
                        $claim isa apt-mechanism-claim-note, has id "{escape_string(claim_id)}";
                        $extract isa note;
                        (claim: $claim, evidence: $extract) isa evidence-chain;
                        $extract has id $eid, has content $econtent;
                    fetch {{ "extract_id": $eid, "content": $econtent }};
                ''').resolve())

            for ext in extract_rows:
                extraction_content = (ext.get("content") or "")[:500]
                ext_id = ext.get("extract_id", "")

                # Find linked paper
                with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx2:
                    paper_rows = list(tx2.query(f'''
                        match
                            $extract isa note, has id "{escape_string(ext_id)}";
                            $paper isa scilit-paper;
                            (note: $extract, subject: $paper) isa aboutness;
                            $paper has id $pid, has name $title;
                        fetch {{ "paper_id": $pid, "title": $title }};
                    ''').resolve())
                if paper_rows:
                    paper_title = paper_rows[0].get("title", "")
                    paper_id = paper_rows[0].get("paper_id", "")

                # Try to get PMID separately (optional attribute)
                if paper_id:
                    with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx3:
                        pmid_rows = list(tx3.query(f'''
                            match $paper isa scilit-paper, has id "{escape_string(paper_id)}",
                                  has pmid $pmid_val;
                            fetch {{ "pmid": $pmid_val }};
                        ''').resolve())
                    if pmid_rows:
                        pmid = pmid_rows[0].get("pmid", "")

                break  # use first extraction note

        evidence_items.append({
            "claim_id": claim_id,
            "support_type": claim.get("support_type", ""),
            "evidence_source": claim.get("evidence_source", ""),
            "snippet": snippet,
            "extraction_content": extraction_content,
            "paper_title": paper_title,
            "paper_id": paper_id,
            "pmid": pmid,
        })

    print(json.dumps({
        "success": True,
        "mechanism_id": mechanism_id,
        "count": len(evidence_items),
        "evidence": evidence_items,
    }, indent=2))


def cmd_search_evidence(args):
    """Semantic search for evidence notes and sections related to a query and MONDO ID."""
    query = args.query
    mondo_id = getattr(args, "mondo_id", "") or ""
    top_k = getattr(args, "top_k", 10) or 10

    if not VOYAGE_API_KEY:
        print(json.dumps({
            "success": False,
            "warning": "VOYAGE_API_KEY not set — semantic search unavailable.",
            "results": [],
        }, indent=2))
        return

    results = []

    # Search apt-notes (claim notes)
    try:
        embedding_client = NoteEmbeddingClient()
        note_hits = embedding_client.search(query=query, mondo_id=mondo_id or None, top_k=top_k)
        for h in note_hits:
            results.append({**h, "layer": "note"})
    except Exception as e:
        print(f"Warning: apt-notes search failed: {e}", file=sys.stderr)

    # Search apt-sections via scilit subprocess
    scilit_script = _find_scilit_script()
    if os.path.isfile(scilit_script):
        import subprocess
        cmd_args = [sys.executable, scilit_script, "search-sections", "--query", query,
                    "--top-k", str(top_k)]
        if mondo_id:
            cmd_args += ["--tag-mondo-id", mondo_id]
        try:
            proc = subprocess.run(cmd_args, capture_output=True, text=True, timeout=60)
            if proc.returncode == 0 and proc.stdout.strip():
                scilit_data = json.loads(proc.stdout)
                for section in scilit_data.get("results", []):
                    results.append({**section, "layer": "fragment"})
        except Exception as e:
            print(f"Warning: scilit search-sections failed: {e}", file=sys.stderr)

    print(json.dumps({
        "success": True,
        "query": query,
        "mondo_id": mondo_id,
        "count": len(results),
        "results": results,
    }, indent=2))


def cmd_fetch_fulltext(args):
    """Fetch PDF and embed sections for a scilit-paper, tagged with a MONDO ID."""
    import subprocess
    scilit_script = _find_scilit_script()
    if not os.path.isfile(scilit_script):
        print(json.dumps({"success": False, "error": f"scilit script not found: {scilit_script}"}))
        return

    paper_id = args.paper_id
    mondo_id = args.mondo_id

    # Step 1: fetch PDF
    print(f"Fetching PDF for {paper_id}...", file=sys.stderr)
    pdf_result = subprocess.run(
        [sys.executable, scilit_script, "fetch-pdf", "--id", paper_id],
        capture_output=True, text=True, timeout=120,
    )
    pdf_ok = pdf_result.returncode == 0
    if not pdf_ok:
        print(f"Warning: fetch-pdf returned exit {pdf_result.returncode}: {pdf_result.stderr[:200]}",
              file=sys.stderr)

    # Step 2: embed sections
    print(f"Embedding sections for {paper_id} (tagged {mondo_id})...", file=sys.stderr)
    embed_result = subprocess.run(
        [sys.executable, scilit_script, "embed-sections",
         "--paper-id", paper_id, "--tag-mondo-id", mondo_id],
        capture_output=True, text=True, timeout=300,
    )
    embed_ok = embed_result.returncode == 0
    section_count = 0
    embedded_count = 0
    if embed_ok and embed_result.stdout.strip():
        try:
            embed_data = json.loads(embed_result.stdout)
            section_count = embed_data.get("section_count", 0)
            embedded_count = embed_data.get("embedded_count", 0)
        except Exception:
            pass

    print(json.dumps({
        "success": embed_ok,
        "paper_id": paper_id,
        "mondo_id": mondo_id,
        "pdf_fetched": pdf_ok,
        "section_count": section_count,
        "embedded_count": embedded_count,
    }, indent=2))


def cmd_extract_mechanism_claims(args):
    """Use Claude to extract mechanistic evidence claims from paper sections."""
    try:
        import anthropic
    except ImportError:
        print(json.dumps({"success": False,
                          "error": "anthropic package not installed. Run: uv add anthropic"}))
        return

    mechanism_id = args.mechanism_id
    paper_id = args.paper_id

    # 1. Fetch mechanism info
    mech_info = _get_mechanism_info(mechanism_id)
    if not mech_info:
        print(json.dumps({"success": False,
                          "error": f"Mechanism not found: {mechanism_id}"}))
        return

    mechanism_type = mech_info.get("mechanism_type", "unknown")
    mechanism_desc = mech_info.get("description", mech_info.get("name", ""))
    mondo_id = mech_info.get("mondo_id", "")

    # 2. Search for relevant sections
    sections = []
    scilit_script = _find_scilit_script()
    if os.path.isfile(scilit_script) and VOYAGE_API_KEY:
        import subprocess
        query_text = f"{mechanism_desc} {mechanism_type}"
        cmd_args = [sys.executable, scilit_script, "search-sections",
                    "--query", query_text, "--top-k", "8",
                    "--paper-id", paper_id]
        try:
            proc = subprocess.run(cmd_args, capture_output=True, text=True, timeout=60)
            if proc.returncode == 0 and proc.stdout.strip():
                scilit_data = json.loads(proc.stdout)
                sections = scilit_data.get("results", [])
        except Exception as e:
            print(f"Warning: search-sections failed: {e}", file=sys.stderr)
    elif not VOYAGE_API_KEY:
        print("Warning: VOYAGE_API_KEY not set; section search skipped.", file=sys.stderr)

    if not sections:
        print(json.dumps({
            "success": False,
            "error": "No sections found. Run fetch-fulltext first.",
            "mechanism_id": mechanism_id,
            "paper_id": paper_id,
        }))
        return

    # 3. Call Claude for each section
    anthropic_client = anthropic.Anthropic()
    claims_created = 0
    sections_searched = len(sections)

    for section in sections:
        section_content = section.get("content", section.get("text", ""))
        if not section_content:
            continue

        prompt = f"""You are analyzing scientific literature to find evidence for a disease mechanism.

Mechanism: {mechanism_desc} (type: {mechanism_type})

Section text:
{section_content[:3000]}

Does this text support, refute, or partially support the mechanism?
Reply ONLY with a JSON object (no markdown, no explanation outside JSON):
{{"support_type": "SUPPORTS|REFUTES|PARTIAL|NO_EVIDENCE", "snippet": "most relevant quote (max 300 chars)", "explanation": "brief explanation", "evidence_source": "HUMAN_CLINICAL|MODEL_ORGANISM|IN_VITRO|COMPUTATIONAL|OTHER"}}"""

        try:
            message = anthropic_client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}],
            )
            raw_text = message.content[0].text.strip()
            # Strip markdown code fences if present
            if raw_text.startswith("```"):
                raw_text = "\n".join(raw_text.split("\n")[1:-1])
            extraction = json.loads(raw_text)
        except Exception as e:
            print(f"Warning: Claude extraction failed for section: {e}", file=sys.stderr)
            continue

        support_type = extraction.get("support_type", "NO_EVIDENCE")
        if support_type == "NO_EVIDENCE":
            continue

        snippet = extraction.get("snippet", section_content[:300])
        explanation = extraction.get("explanation", "")
        evidence_source = extraction.get("evidence_source", "OTHER")

        # Insert evidence directly using the same logic as cmd_add_evidence
        timestamp = get_timestamp()
        extract_id = generate_id("scilit-extract")
        claim_id = generate_id("apt-claim-note")
        claim_name = f"Claim: {mechanism_type} - {support_type}"
        extract_content = snippet
        if explanation:
            extract_content += f"\n\nExplanation: {explanation}"

        try:
            with get_driver() as driver:
                with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
                    tx.query(f'''insert $n isa scilit-extraction-note,
                        has id "{extract_id}",
                        has name "Evidence: {escape_string(snippet[:60])}",
                        has content "{escape_string(extract_content)}",
                        has created-at {timestamp};''').resolve()
                    tx.commit()

                with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
                    tx.query(f'''match
                        $n isa scilit-extraction-note, has id "{extract_id}";
                        $p isa scilit-paper, has id "{escape_string(paper_id)}";
                    insert (note: $n, subject: $p) isa aboutness;''').resolve()
                    tx.commit()

                with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
                    tx.query(f'''insert $n isa apt-mechanism-claim-note,
                        has id "{claim_id}",
                        has name "{escape_string(claim_name)}",
                        has content "{escape_string(snippet)}",
                        has apt-mechanism-type "{escape_string(mechanism_type)}",
                        has apt-support-type "{escape_string(support_type)}",
                        has apt-evidence-source "{escape_string(evidence_source)}",
                        has created-at {timestamp};''').resolve()
                    tx.commit()

                with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
                    tx.query(f'''match
                        $n isa apt-mechanism-claim-note, has id "{claim_id}";
                        $m isa apt-mechanism, has id "{escape_string(mechanism_id)}";
                    insert (note: $n, subject: $m) isa aboutness;''').resolve()
                    tx.commit()

                with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
                    tx.query(f'''match
                        $claim isa apt-mechanism-claim-note, has id "{claim_id}";
                        $extract isa scilit-extraction-note, has id "{extract_id}";
                    insert (claim: $claim, evidence: $extract) isa evidence-chain;''').resolve()
                    tx.commit()

            claims_created += 1

            # Optional embedding
            if VOYAGE_API_KEY:
                try:
                    ec = NoteEmbeddingClient()
                    ec.embed_note(
                        note_id=claim_id,
                        content=snippet,
                        metadata={
                            "note_type": "apt-mechanism-claim-note",
                            "mechanism_id": mechanism_id,
                            "mondo_id": mondo_id,
                            "support_type": support_type,
                        },
                    )
                except Exception:
                    pass

        except Exception as e:
            print(f"Warning: failed to store claim for section: {e}", file=sys.stderr)
            continue

    print(json.dumps({
        "success": True,
        "mechanism_id": mechanism_id,
        "paper_id": paper_id,
        "sections_searched": sections_searched,
        "claims_created": claims_created,
    }, indent=2))


def cmd_build_corpus(args):
    """Print ready-to-run scientific-literature CLI commands (360-view strategy)."""
    mondo_id = args.mondo_id
    if not mondo_id.startswith("MONDO:"):
        mondo_id = f"MONDO:{mondo_id}"

    disease = get_disease_by_mondo(mondo_id)
    if not disease:
        print(json.dumps({"success": False, "error": f"Disease not found: {mondo_id}"}))
        return

    disease_name = disease.get("name", mondo_id)
    disease_id = disease["id"]

    # Get causal gene symbols
    with get_driver() as driver:
        with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
            genes = list(tx.query(f'''
                match
                    $d isa apt-disease, has id "{escape_string(disease_id)}";
                    (gene: $g, disease: $d) isa apt-gene-causes-disease;
                fetch {{ "symbol": $g.apt-gene-symbol }};
            ''').resolve())

    gene_symbols = [g.get("symbol") for g in genes if g.get("symbol")]

    import shlex as _shlex

    script = ".claude/skills/scientific-literature/scientific_literature.py"
    # Each entry: (query_string, collection_name, max_results)
    # query_string is the raw value passed to --query (may contain EPMC phrase quotes)
    query_specs = []

    # --- Tier 1: Disease identity ---
    dn = disease_name[:80]
    query_specs.append((f'"{disease_name}"', f"{dn} general", 50))
    synonyms = _fetch_disease_synonyms(mondo_id)
    for syn in synonyms[:3]:
        safe = syn.replace('"', '').replace("\\", "")
        query_specs.append((f'"{safe}"', f"{safe[:40]}", 30))

    # --- Tier 2: Gene + gene aliases ---
    for sym in gene_symbols[:5]:
        query_specs.append((f'{sym} "{disease_name}"', f"{sym} disease", 30))
        aliases = _fetch_gene_aliases(sym)
        for alias in aliases[:2]:
            query_specs.append((f'"{alias}" disease mechanism', f"{alias} mechanism", 20))

    # --- Tier 3: Molecular function (generic) ---
    for sym in gene_symbols[:3]:
        query_specs.append((f'{sym} mechanism pathway biology', f"{sym} mechanism", 25))
        query_specs.append((f'{sym} mutation variant pathogenic', f"{sym} variants", 25))

    # --- Tier 4: Phenotype-driven (from TypeDB) ---
    with get_driver() as driver:
        top_phenotypes = _fetch_top_phenotypes(driver, disease_id)[:5]
    for phenotype in top_phenotypes:
        for sym in gene_symbols[:2]:
            safe_phen = phenotype.replace('"', '').replace("\\", "")
            query_specs.append((f'{sym} "{safe_phen}"', f"{sym} {safe_phen[:20]}", 15))

    # --- Tier 5: Therapeutic ---
    query_specs.append((f'"{disease_name}" treatment therapy', f"{dn[:30]} therapy", 30))
    for sym in gene_symbols[:3]:
        query_specs.append((f'{sym} inhibitor therapeutic drug repurposing', f"{sym} therapeutics", 20))

    # Build as arg lists (avoids shlex double-quote issues with phrase-search queries)
    # Display strings are shell-quoted for copy-paste
    arg_lists = [
        ["uv", "run", "python", script, "search", "--source", "epmc",
         "--query", q, "--collection", col, "--max-results", str(n)]
        for q, col, n in query_specs
    ]
    commands = [" ".join(_shlex.quote(a) for a in al) for al in arg_lists]

    if getattr(args, "execute", False):
        import subprocess
        results_by_cmd = []
        for cmd_str, arg_list in zip(commands, arg_lists):
            try:
                result = subprocess.run(
                    arg_list,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                try:
                    cmd_result = json.loads(result.stdout)
                except json.JSONDecodeError:
                    cmd_result = {"raw": result.stdout[:200], "stderr": result.stderr[:200]}
                results_by_cmd.append({"command": cmd_str, "result": cmd_result})
            except Exception as e:
                results_by_cmd.append({"command": cmd_str, "error": str(e)})

        if getattr(args, "link_to_investigation", None):
            inv_note_id = generate_id("apt-note")
            note_content = (
                f"Literature corpus built for {disease_name}. "
                f"Collections: {len(commands)} search queries executed."
            )
            timestamp = get_timestamp()
            with get_driver() as driver:
                with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
                    tx.query(f'''insert $n isa apt-literature-synthesis-note,
                        has id "{inv_note_id}",
                        has name "Literature corpus: {escape_string(disease_name[:80])}",
                        has content "{escape_string(note_content)}",
                        has created-at {timestamp};''').resolve()
                    tx.commit()
                with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
                    tx.query(f'''match
                        $n isa note, has id "{inv_note_id}";
                        $e isa identifiable-entity, has id "{escape_string(args.link_to_investigation)}";
                    insert (note: $n, subject: $e) isa aboutness;''').resolve()
                    tx.commit()

        print(json.dumps({
            "success": True,
            "disease": disease_name,
            "executed": len(results_by_cmd),
            "results": results_by_cmd,
        }, indent=2))
    else:
        print(json.dumps({
            "success": True,
            "disease": disease_name,
            "commands": commands,
            "instructions": "Copy-paste these commands to build a literature corpus for mechanism analysis.",
        }, indent=2))


# =============================================================================
# ARGUMENT PARSER
# =============================================================================


def build_parser():
    parser = argparse.ArgumentParser(
        description="Algorithm for Precision Therapeutics - Mechanism-centered rare disease investigation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # search-disease
    p = sub.add_parser("search-disease", help="Search Monarch Initiative for diseases")
    p.add_argument("--query", required=True, help="Disease name search query")
    p.add_argument("--limit", type=int, default=10, help="Max results (default: 10)")

    # init-investigation
    p = sub.add_parser("init-investigation", help="Initialize investigation from MONDO ID")
    p.add_argument("mondo_id", help="MONDO disease ID (e.g. MONDO:0800044)")

    # list-investigations
    sub.add_parser("list-investigations", help="List all investigations")

    # ingest-disease
    p = sub.add_parser("ingest-disease", help="Full ingestion pipeline")
    p.add_argument("--mondo-id", required=True, help="MONDO ID")

    # ingest-phenotypes
    p = sub.add_parser("ingest-phenotypes", help="Ingest HPO phenotype associations")
    p.add_argument("--disease", required=True, help="Disease entity ID")

    # ingest-genes
    p = sub.add_parser("ingest-genes", help="Ingest causal and correlated gene associations")
    p.add_argument("--disease", required=True, help="Disease entity ID")

    # ingest-hierarchy
    p = sub.add_parser("ingest-hierarchy", help="Ingest MONDO disease hierarchy")
    p.add_argument("--disease", required=True, help="Disease entity ID")

    # ingest-clintrials
    p = sub.add_parser("ingest-clintrials", help="Ingest clinical trials (name + MONDO ID)")
    p.add_argument("--disease", required=True, help="Disease entity ID")

    # ingest-drugs
    p = sub.add_parser("ingest-drugs", help="Ingest drug candidates from ChEMBL (gene + indication)")
    p.add_argument("--disease", required=True, help="Disease entity ID")

    # ingest-omim
    p = sub.add_parser("ingest-omim", help="Ingest OMIM entry (requires OMIM_API_KEY)")
    p.add_argument("--disease", required=True, help="Disease entity ID")

    # add-mechanism
    p = sub.add_parser("add-mechanism", help="Add a mechanism of harm entity")
    p.add_argument("--disease", required=True, help="Disease entity ID")
    p.add_argument("--type", required=True, choices=MECHANISM_TYPES, help="Mechanism type")
    p.add_argument("--level", required=True,
                   choices=["molecular", "cellular", "tissue", "systemic"],
                   help="Mechanism level")
    p.add_argument("--description", required=True, help="Mechanism description")

    # add-gene
    p = sub.add_parser("add-gene", help="Add a gene entity")
    p.add_argument("--symbol", required=True, help="Gene symbol (e.g. NGLY1)")
    p.add_argument("--hgnc-id", dest="hgnc_id", default="", help="HGNC ID")

    # add-drug
    p = sub.add_parser("add-drug", help="Add a drug entity")
    p.add_argument("--name", required=True, help="Drug name")
    p.add_argument("--chembl-id", dest="chembl_id", default="", help="ChEMBL ID")
    p.add_argument("--modality", default="", help="Therapeutic modality")
    p.add_argument("--moa", default="", help="Mechanism of action")

    # add-strategy
    p = sub.add_parser("add-strategy", help="Add a therapeutic strategy")
    p.add_argument("--mechanism", required=True, help="Mechanism entity ID")
    p.add_argument("--modality", required=True, help="Therapeutic modality")
    p.add_argument("--rationale", required=True, help="Strategy rationale")

    # add-phenotype
    p = sub.add_parser("add-phenotype", help="Add a phenotype and link to disease")
    p.add_argument("--hpo-id", dest="hpo_id", required=True, help="HPO ID (e.g. HP:0001234)")
    p.add_argument("--disease", required=True, help="Disease entity ID")
    p.add_argument("--frequency", default="", help="Frequency qualifier")

    # link-mechanism-gene
    p = sub.add_parser("link-mechanism-gene", help="Link mechanism to gene")
    p.add_argument("--mechanism", required=True, help="Mechanism entity ID")
    p.add_argument("--gene", required=True, help="Gene entity ID")

    # link-mechanism-phenotype
    p = sub.add_parser("link-mechanism-phenotype", help="Link mechanism to phenotype")
    p.add_argument("--mechanism", required=True, help="Mechanism entity ID")
    p.add_argument("--phenotype", required=True, help="Phenotype entity ID")

    # link-drug-mechanism
    p = sub.add_parser("link-drug-mechanism", help="Link drug to mechanism via strategy")
    p.add_argument("--drug", required=True, help="Drug entity ID")
    p.add_argument("--mechanism", required=True, help="Mechanism entity ID")

    # link-drug-target
    p = sub.add_parser("link-drug-target", help="Link drug to gene target")
    p.add_argument("--drug", required=True, help="Drug entity ID")
    p.add_argument("--gene", required=True, help="Gene entity ID")
    p.add_argument("--moa", default="", help="Mechanism of action")

    # list-artifacts
    p = sub.add_parser("list-artifacts", help="List artifacts")
    p.add_argument("--disease", default="", help="Filter by disease entity ID")

    # show-artifact
    p = sub.add_parser("show-artifact", help="Get artifact content")
    p.add_argument("--id", required=True, help="Artifact entity ID")

    # show-disease
    p = sub.add_parser("show-disease", help="Full disease overview")
    p.add_argument("--mondo-id", dest="mondo_id", required=True, help="MONDO ID")

    # show-mechanisms
    p = sub.add_parser("show-mechanisms", help="All mechanisms with links")
    p.add_argument("--mondo-id", dest="mondo_id", required=True, help="MONDO ID")

    # show-therapeutic-map
    p = sub.add_parser("show-therapeutic-map", help="Therapeutic strategies per mechanism")
    p.add_argument("--mondo-id", dest="mondo_id", required=True, help="MONDO ID")

    # show-phenome
    p = sub.add_parser("show-phenome", help="Phenotypic spectrum by frequency tier")
    grp = p.add_mutually_exclusive_group(required=True)
    grp.add_argument("--disease", default="", help="Disease entity ID")
    grp.add_argument("--mondo-id", dest="mondo_id", default="", help="MONDO ID")

    # show-genes
    p = sub.add_parser("show-genes", help="Causal genes with evidence")
    p.add_argument("--mondo-id", dest="mondo_id", required=True, help="MONDO ID")

    # show-trials
    p = sub.add_parser("show-trials", help="Clinical trials landscape")
    p.add_argument("--mondo-id", dest="mondo_id", required=True, help="MONDO ID")

    # show-gaps
    p = sub.add_parser("show-gaps", help="Undrugged mechanisms, unexplained phenotypes, orphan genes")
    p.add_argument("--mondo-id", dest="mondo_id", required=True, help="MONDO ID")

    # show-repurposing
    p = sub.add_parser("show-repurposing", help="Repurposing opportunities via shared mechanism types")
    p.add_argument("--mondo-id", dest="mondo_id", default="", help="Filter to this disease + siblings")

    # show-sibling-diseases
    p = sub.add_parser("show-sibling-diseases", help="Diseases sharing mechanism types")
    p.add_argument("--mondo-id", dest="mondo_id", required=True, help="MONDO ID")

    # export-report
    p = sub.add_parser("export-report", help="Export comprehensive Markdown report")
    p.add_argument("--mondo-id", dest="mondo_id", required=True, help="MONDO ID")
    p.add_argument("--output", default="", help="Output file path (default: stdout)")

    # add-note
    p = sub.add_parser("add-note", help="Create a note about an entity")
    p.add_argument("--entity", required=True, help="Entity ID to annotate")
    p.add_argument("--type", default="apt-disease-overview-note", help="Note type")
    p.add_argument("--content", required=True, help="Note content")

    # tag
    p = sub.add_parser("tag", help="Tag an entity")
    p.add_argument("--entity", required=True, help="Entity ID")
    p.add_argument("--tag", required=True, help="Tag value")

    # search-tag
    p = sub.add_parser("search-tag", help="Search entities by tag")
    p.add_argument("--tag", required=True, help="Tag to search for")

    # build-corpus
    p = sub.add_parser("build-corpus", help="Print or execute scientific-literature CLI commands (360-view)")
    p.add_argument("--mondo-id", dest="mondo_id", required=True, help="MONDO ID")
    p.add_argument("--execute", action="store_true", help="Execute commands (not just print)")
    p.add_argument("--link-to-investigation", dest="link_to_investigation", default="",
                   help="Link synthesis note to this investigation ID")

    # add-evidence
    p = sub.add_parser("add-evidence", help="Add literature evidence for a mechanism")
    p.add_argument("--mechanism-id", dest="mechanism_id", required=True,
                   help="Mechanism entity ID")
    p.add_argument("--pmid", required=True, help="PubMed ID of supporting paper")
    p.add_argument("--snippet", required=True, help="Relevant text snippet from paper")
    p.add_argument("--support-type", dest="support_type", required=True,
                   choices=["SUPPORTS", "REFUTES", "PARTIAL"],
                   help="How this evidence relates to the mechanism")
    p.add_argument("--evidence-source", dest="evidence_source", required=True,
                   choices=["HUMAN_CLINICAL", "MODEL_ORGANISM", "IN_VITRO",
                            "COMPUTATIONAL", "OTHER"],
                   help="Type of experimental evidence")
    p.add_argument("--explanation", default="", help="Optional explanation of relevance")

    # show-evidence
    p = sub.add_parser("show-evidence", help="Show all evidence claims for a mechanism")
    p.add_argument("--mechanism-id", dest="mechanism_id", required=True,
                   help="Mechanism entity ID")

    # search-evidence
    p = sub.add_parser("search-evidence", help="Semantic search for evidence notes and sections")
    p.add_argument("--query", required=True, help="Search query text")
    p.add_argument("--mondo-id", dest="mondo_id", default="",
                   help="Filter to this MONDO ID (optional)")
    p.add_argument("--top-k", dest="top_k", type=int, default=10,
                   help="Max results to return (default: 10)")

    # fetch-fulltext
    p = sub.add_parser("fetch-fulltext",
                       help="Fetch PDF and embed sections for a paper (tagged by MONDO ID)")
    p.add_argument("--paper-id", dest="paper_id", required=True,
                   help="scilit-paper entity ID")
    p.add_argument("--mondo-id", dest="mondo_id", required=True,
                   help="MONDO ID to tag sections with")

    # extract-mechanism-claims
    p = sub.add_parser("extract-mechanism-claims",
                       help="Use Claude to extract mechanistic claims from paper sections")
    p.add_argument("--mechanism-id", dest="mechanism_id", required=True,
                   help="Mechanism entity ID")
    p.add_argument("--paper-id", dest="paper_id", required=True,
                   help="scilit-paper entity ID")

    return parser


COMMAND_MAP = {
    "search-disease": cmd_search_disease,
    "init-investigation": cmd_init_investigation,
    "list-investigations": cmd_list_investigations,
    "ingest-disease": cmd_ingest_disease,
    "ingest-phenotypes": cmd_ingest_phenotypes,
    "ingest-genes": cmd_ingest_genes,
    "ingest-hierarchy": cmd_ingest_hierarchy,
    "ingest-clintrials": cmd_ingest_clintrials,
    "ingest-drugs": cmd_ingest_drugs,
    "ingest-omim": cmd_ingest_omim,
    "add-mechanism": cmd_add_mechanism,
    "add-gene": cmd_add_gene,
    "add-drug": cmd_add_drug,
    "add-strategy": cmd_add_strategy,
    "add-phenotype": cmd_add_phenotype,
    "link-mechanism-gene": cmd_link_mechanism_gene,
    "link-mechanism-phenotype": cmd_link_mechanism_phenotype,
    "link-drug-mechanism": cmd_link_drug_mechanism,
    "link-drug-target": cmd_link_drug_target,
    "list-artifacts": cmd_list_artifacts,
    "show-artifact": cmd_show_artifact,
    "show-disease": cmd_show_disease,
    "show-mechanisms": cmd_show_mechanisms,
    "show-therapeutic-map": cmd_show_therapeutic_map,
    "show-phenome": cmd_show_phenome,
    "show-genes": cmd_show_genes,
    "show-trials": cmd_show_trials,
    "show-gaps": cmd_show_gaps,
    "show-repurposing": cmd_show_repurposing,
    "show-sibling-diseases": cmd_show_sibling_diseases,
    "export-report": cmd_export_report,
    "add-note": cmd_add_note,
    "tag": cmd_tag,
    "search-tag": cmd_search_tag,
    "build-corpus": cmd_build_corpus,
    "add-evidence": cmd_add_evidence,
    "show-evidence": cmd_show_evidence,
    "search-evidence": cmd_search_evidence,
    "fetch-fulltext": cmd_fetch_fulltext,
    "extract-mechanism-claims": cmd_extract_mechanism_claims,
}


def main():
    if not TYPEDB_AVAILABLE:
        print(json.dumps({
            "error": "TypeDB driver not available. Run: uv sync --all-extras",
        }))
        sys.exit(1)

    parser = build_parser()
    args = parser.parse_args()

    cmd = COMMAND_MAP.get(args.command)
    if not cmd:
        print(json.dumps({"error": f"Unknown command: {args.command}"}))
        sys.exit(1)

    cmd(args)


if __name__ == "__main__":
    main()
