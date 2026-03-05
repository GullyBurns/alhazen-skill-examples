#!/usr/bin/env python3
"""
Literature CLI - Multi-source scientific paper search and ingestion.

Supported sources: pubmed, openalex, biorxiv, medrxiv

Usage:
    python literature.py search --source pubmed --query "CRISPR" --collection "col-abc"
    python literature.py ingest --doi "10.1038/s41587-020-0700-8"
    python literature.py show --id "scilit-paper-abc123"
    python literature.py list [--collection "col-abc"]
    python literature.py embed --collection "collection-abc123"
    python literature.py search-semantic --query "CDK8 stress response" --collection "col-abc"
    python literature.py cluster --collection "collection-abc123" --min-cluster-size 15 --dry-run

Environment:
    TYPEDB_HOST         TypeDB host (default: localhost)
    TYPEDB_PORT         TypeDB port (default: 1729)
    TYPEDB_DATABASE     Database name (default: alhazen_notebook)
    NCBI_API_KEY        NCBI Entrez API key (optional; raises rate limit to 10 req/s)
    OPENALEX_API_KEY    OpenAlex API key (optional; free at openalex.org/settings/api)
    VOYAGE_API_KEY      Voyage AI API key (required for embed/search-semantic/cluster)
    QDRANT_HOST         Qdrant host (default: localhost)
    QDRANT_PORT         Qdrant port (default: 6333)
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from typedb.driver import Credentials, DriverOptions, TransactionType, TypeDB
    TYPEDB_AVAILABLE = True
except ImportError:
    TYPEDB_AVAILABLE = False
    print("Warning: typedb-driver not installed.", file=sys.stderr)

try:
    from skillful_alhazen.utils.skill_helpers import escape_string, generate_id, get_timestamp
except ImportError:
    import uuid
    from datetime import datetime, timezone

    def escape_string(s):
        if s is None:
            return ""
        return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "")

    def generate_id(prefix):
        return f"{prefix}-{uuid.uuid4().hex[:12]}"

    def get_timestamp():
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("Warning: requests not installed. Run: uv add requests", file=sys.stderr)

try:
    import xml.etree.ElementTree as ET
    XML_AVAILABLE = True
except ImportError:
    XML_AVAILABLE = False


# =============================================================================
# CONFIGURATION
# =============================================================================

TYPEDB_HOST = os.getenv("TYPEDB_HOST", "localhost")
TYPEDB_PORT = int(os.getenv("TYPEDB_PORT", "1729"))
TYPEDB_DATABASE = os.getenv("TYPEDB_DATABASE", "alhazen_notebook")
TYPEDB_USERNAME = os.getenv("TYPEDB_USERNAME", "admin")
TYPEDB_PASSWORD = os.getenv("TYPEDB_PASSWORD", "password")

NCBI_API_KEY = os.getenv("NCBI_API_KEY", "")
OPENALEX_API_KEY = os.getenv("OPENALEX_API_KEY", "")
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY", "")

NCBI_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
OPENALEX_BASE = "https://api.openalex.org"
BIORXIV_BASE = "https://api.biorxiv.org/pubs"
MEDRXIV_BASE = "https://api.medrxiv.org/pubs"

HEADERS = {"User-Agent": "skillful-alhazen/0.1 (mailto:alhazen@example.com)"}


# =============================================================================
# TYPEDB HELPERS
# =============================================================================

def get_driver():
    return TypeDB.driver(
        f"{TYPEDB_HOST}:{TYPEDB_PORT}",
        Credentials(TYPEDB_USERNAME, TYPEDB_PASSWORD),
        DriverOptions(is_tls_enabled=False),
    )


def paper_exists(driver, doi=None, pmid=None):
    """Check if a paper already exists by DOI or PMID."""
    with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
        if doi:
            result = list(tx.query(
                f'match $p isa scilit-paper, has doi "{escape_string(doi)}"; fetch {{ "id": $p.id }};'
            ).resolve())
            if result:
                return result[0]["id"]
        if pmid:
            result = list(tx.query(
                f'match $p isa scilit-paper, has pmid "{escape_string(pmid)}"; fetch {{ "id": $p.id }};'
            ).resolve())
            if result:
                return result[0]["id"]
    return None


def insert_paper(driver, paper: dict) -> str:
    """Insert a normalized paper dict into TypeDB. Returns paper_id."""
    pid = paper.get("id") or generate_id("scilit-paper")
    timestamp = get_timestamp()

    q = f'insert $p isa scilit-paper, has id "{pid}", has name "{escape_string(paper.get("title", ""))}"'
    if paper.get("abstract"):
        q += f', has abstract-text "{escape_string(paper["abstract"])}"'
    if paper.get("doi"):
        q += f', has doi "{escape_string(paper["doi"])}"'
    if paper.get("pmid"):
        q += f', has pmid "{escape_string(str(paper["pmid"]))}"'
    if paper.get("pmcid"):
        q += f', has pmcid "{escape_string(paper["pmcid"])}"'
    if paper.get("arxiv_id"):
        q += f', has arxiv-id "{escape_string(paper["arxiv_id"])}"'
    if paper.get("year"):
        q += f', has publication-year {int(paper["year"])}'
    if paper.get("journal"):
        q += f', has journal-name "{escape_string(paper["journal"])}"'
    q += f', has source-uri "{escape_string(paper.get("source_uri", ""))}", has created-at {timestamp};'

    with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
        tx.query(q).resolve()
        tx.commit()

    return pid


def add_to_collection(driver, paper_id: str, collection_id: str):
    """Add a paper to a collection."""
    with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
        tx.query(
            f'match $c isa collection, has id "{collection_id}"; '
            f'$p isa scilit-paper, has id "{paper_id}"; '
            f'insert (collection: $c, member: $p) isa collection-membership;'
        ).resolve()
        tx.commit()


# =============================================================================
# SOURCE CONNECTORS
# =============================================================================

def _ncbi_params(**kwargs):
    params = {"retmode": "json", **kwargs}
    if NCBI_API_KEY:
        params["api_key"] = NCBI_API_KEY
    return params


def search_pubmed(query: str, max_results: int = 20) -> list[dict]:
    """Search PubMed via Entrez esearch + efetch. Returns normalized paper dicts."""
    if not REQUESTS_AVAILABLE:
        raise RuntimeError("requests not installed")

    # Step 1: esearch to get PMIDs
    r = requests.get(
        f"{NCBI_BASE}/esearch.fcgi",
        params=_ncbi_params(db="pubmed", term=query, retmax=max_results, usehistory="y"),
        headers=HEADERS,
        timeout=30,
    )
    r.raise_for_status()
    search_data = r.json()
    id_list = search_data.get("esearchresult", {}).get("idlist", [])
    if not id_list:
        return []

    time.sleep(0.34)  # NCBI rate limit: 3 req/s without key

    # Step 2: efetch to get full records (XML is richer than JSON for PubMed)
    r = requests.get(
        f"{NCBI_BASE}/efetch.fcgi",
        params=_ncbi_params(db="pubmed", id=",".join(id_list), rettype="abstract", retmode="xml"),
        headers=HEADERS,
        timeout=60,
    )
    r.raise_for_status()

    return _parse_pubmed_xml(r.text)


def _parse_pubmed_xml(xml_text: str) -> list[dict]:
    """Parse PubMed efetch XML into normalized dicts."""
    papers = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    for article in root.findall(".//PubmedArticle"):
        medline = article.find(".//MedlineCitation")
        if medline is None:
            continue

        pmid_el = medline.find("PMID")
        pmid = pmid_el.text if pmid_el is not None else None

        art = medline.find("Article")
        if art is None:
            continue

        title_el = art.find("ArticleTitle")
        title = "".join(title_el.itertext()) if title_el is not None else ""

        abstract_el = art.find(".//AbstractText")
        abstract = "".join(abstract_el.itertext()) if abstract_el is not None else ""

        journal_el = art.find(".//Journal/Title")
        journal = journal_el.text if journal_el is not None else ""

        year_el = art.find(".//PubDate/Year")
        year = int(year_el.text) if year_el is not None and year_el.text else None

        # DOI from ArticleIdList
        doi = None
        for aid in article.findall(".//ArticleId"):
            if aid.get("IdType") == "doi":
                doi = aid.text
                break

        papers.append({
            "title": title.strip(),
            "abstract": abstract.strip(),
            "pmid": pmid,
            "doi": doi,
            "journal": journal,
            "year": year,
            "source_uri": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
        })

    return papers


def search_openalex(query: str, max_results: int = 20) -> list[dict]:
    """Search OpenAlex /works endpoint. Returns normalized paper dicts."""
    if not REQUESTS_AVAILABLE:
        raise RuntimeError("requests not installed")

    params = {
        "search": query,
        "per_page": min(max_results, 200),
        "select": "id,display_name,abstract_inverted_index,doi,ids,publication_year,primary_location,type",
    }
    if OPENALEX_API_KEY:
        params["api_key"] = OPENALEX_API_KEY

    r = requests.get(
        f"{OPENALEX_BASE}/works",
        params=params,
        headers=HEADERS,
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()

    papers = []
    for work in data.get("results", []):
        papers.append(_normalize_openalex(work))
    return papers


def _normalize_openalex(work: dict) -> dict:
    """Convert OpenAlex work dict to normalized paper dict."""
    # Reconstruct abstract from inverted index
    abstract = ""
    aii = work.get("abstract_inverted_index")
    if aii:
        words = [""] * (max(max(v) for v in aii.values()) + 1)
        for word, positions in aii.items():
            for pos in positions:
                words[pos] = word
        abstract = " ".join(w for w in words if w)

    ids = work.get("ids", {})
    pmid = ids.get("pmid", "")
    if pmid and pmid.startswith("https://pubmed.ncbi.nlm.nih.gov/"):
        pmid = pmid.split("/")[-2] if pmid.endswith("/") else pmid.split("/")[-1]

    doi = work.get("doi", "") or ""
    if doi.startswith("https://doi.org/"):
        doi = doi[len("https://doi.org/"):]

    journal = ""
    primary_loc = work.get("primary_location") or {}
    source = primary_loc.get("source") or {}
    journal = source.get("display_name", "")

    return {
        "title": work.get("display_name", ""),
        "abstract": abstract,
        "doi": doi,
        "pmid": pmid,
        "year": work.get("publication_year"),
        "journal": journal,
        "source_uri": work.get("id", ""),
    }


def search_biorxiv(query: str, max_results: int = 20, server: str = "biorxiv") -> list[dict]:
    """
    Search bioRxiv/medRxiv. Because the API only supports date ranges
    (no full-text search), we fetch recent preprints and filter by keyword.
    """
    if not REQUESTS_AVAILABLE:
        raise RuntimeError("requests not installed")

    base = BIORXIV_BASE if server == "biorxiv" else MEDRXIV_BASE
    papers = []
    cursor = 0
    query_lower = query.lower()

    while len(papers) < max_results:
        r = requests.get(
            f"{base}/{server}/30d/{cursor}",  # last 30 days
            headers=HEADERS,
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        collection = data.get("collection", [])
        if not collection:
            break

        for item in collection:
            title = item.get("title", "")
            abstract = item.get("abstract", "")
            # Client-side keyword filter
            if query_lower in title.lower() or query_lower in abstract.lower():
                doi = item.get("doi", "")
                papers.append({
                    "title": title,
                    "abstract": abstract,
                    "doi": doi,
                    "arxiv_id": None,
                    "year": int(item.get("date", "0000")[:4]) if item.get("date") else None,
                    "journal": f"{server.capitalize()} preprint",
                    "source_uri": f"https://doi.org/{doi}" if doi else "",
                })
            if len(papers) >= max_results:
                break

        cursor += 100
        if len(collection) < 100:
            break
        time.sleep(0.5)

    return papers[:max_results]


def fetch_by_doi_openalex(doi: str) -> dict | None:
    """Fetch a single work by DOI from OpenAlex."""
    if not REQUESTS_AVAILABLE:
        return None
    params = {"select": "id,display_name,abstract_inverted_index,doi,ids,publication_year,primary_location"}
    if OPENALEX_API_KEY:
        params["api_key"] = OPENALEX_API_KEY
    try:
        r = requests.get(
            f"{OPENALEX_BASE}/works/https://doi.org/{doi}",
            params=params,
            headers=HEADERS,
            timeout=30,
        )
        r.raise_for_status()
        return _normalize_openalex(r.json())
    except Exception:
        return None


def fetch_by_doi_ncbi(doi: str) -> dict | None:
    """Fetch a paper by DOI via NCBI esearch."""
    if not REQUESTS_AVAILABLE:
        return None
    try:
        r = requests.get(
            f"{NCBI_BASE}/esearch.fcgi",
            params=_ncbi_params(db="pubmed", term=f"{doi}[doi]", retmax=1),
            headers=HEADERS,
            timeout=30,
        )
        r.raise_for_status()
        ids = r.json().get("esearchresult", {}).get("idlist", [])
        if not ids:
            return None
        time.sleep(0.34)
        papers = search_pubmed(f"{doi}[doi]", max_results=1)
        return papers[0] if papers else None
    except Exception:
        return None


# =============================================================================
# COMMANDS
# =============================================================================

def cmd_search(args):
    """Search a literature source and store results in TypeDB."""
    source = args.source.lower()
    query = args.query
    max_results = args.max_results

    print(f"Searching {source} for: {query}", file=sys.stderr)

    if source == "pubmed":
        papers = search_pubmed(query, max_results)
    elif source == "openalex":
        papers = search_openalex(query, max_results)
    elif source in ("biorxiv", "medrxiv"):
        papers = search_biorxiv(query, max_results, server=source)
    else:
        print(json.dumps({"success": False, "error": f"Unknown source: {source}"}))
        sys.exit(1)

    if not papers:
        print(json.dumps({"success": True, "inserted": 0, "skipped": 0, "papers": []}))
        return

    inserted = 0
    skipped = 0
    result_papers = []

    with get_driver() as driver:
        for paper in papers:
            existing_id = paper_exists(driver, doi=paper.get("doi"), pmid=paper.get("pmid"))
            if existing_id:
                skipped += 1
                result_papers.append({"id": existing_id, "title": paper["title"], "status": "existing"})
                continue

            pid = insert_paper(driver, paper)
            inserted += 1
            result_papers.append({"id": pid, "title": paper["title"], "status": "inserted"})

            if args.collection:
                try:
                    add_to_collection(driver, pid, args.collection)
                except Exception as e:
                    print(f"Warning: could not add {pid} to collection: {e}", file=sys.stderr)

    print(json.dumps({
        "success": True,
        "source": source,
        "query": query,
        "inserted": inserted,
        "skipped": skipped,
        "papers": result_papers,
    }, indent=2))


def cmd_ingest(args):
    """Fetch and store a single paper by DOI."""
    doi = args.doi.strip()
    if doi.startswith("https://doi.org/"):
        doi = doi[len("https://doi.org/"):]

    print(f"Ingesting DOI: {doi}", file=sys.stderr)

    with get_driver() as driver:
        existing_id = paper_exists(driver, doi=doi)
        if existing_id:
            print(json.dumps({"success": True, "paper_id": existing_id, "status": "existing"}))
            return

        # Try OpenAlex first (JSON, richer abstract)
        paper = fetch_by_doi_openalex(doi)
        if not paper or not paper.get("title"):
            paper = fetch_by_doi_ncbi(doi)
        if not paper:
            print(json.dumps({"success": False, "error": f"Could not find DOI: {doi}"}))
            sys.exit(1)

        pid = insert_paper(driver, paper)
        if args.collection:
            try:
                add_to_collection(driver, pid, args.collection)
            except Exception as e:
                print(f"Warning: {e}", file=sys.stderr)

    print(json.dumps({
        "success": True,
        "paper_id": pid,
        "title": paper.get("title"),
        "doi": doi,
        "status": "inserted",
    }, indent=2))


def cmd_show(args):
    """Show a paper's details for sensemaking."""
    with get_driver() as driver:
        with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
            result = list(tx.query(
                f'match $p isa scilit-paper, has id "{args.id}"; '
                f'fetch {{ "id": $p.id, "name": $p.name, "abstract-text": $p.abstract-text, '
                f'"doi": $p.doi, "pmid": $p.pmid, "year": $p.publication-year, '
                f'"journal": $p.journal-name, "source-uri": $p.source-uri }};'
            ).resolve())

            if not result:
                print(json.dumps({"success": False, "error": "Paper not found"}))
                sys.exit(1)

            # Get notes
            notes = list(tx.query(
                f'match $p isa scilit-paper, has id "{args.id}"; '
                f'(note: $n, subject: $p) isa aboutness; '
                f'fetch {{ "id": $n.id, "name": $n.name, "content": $n.content }};'
            ).resolve())

    paper = {k: v for k, v in result[0].items() if v is not None}
    print(json.dumps({
        "success": True,
        "paper": paper,
        "notes": [{k: v for k, v in n.items() if v is not None} for n in notes],
    }, indent=2))


def cmd_list(args):
    """List papers, optionally filtered by collection."""
    with get_driver() as driver:
        with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
            if args.collection:
                query = (
                    f'match $c isa collection, has id "{args.collection}"; '
                    f'(collection: $c, member: $p) isa collection-membership; '
                    f'$p isa scilit-paper; '
                    f'fetch {{ "id": $p.id, "name": $p.name, "doi": $p.doi, "year": $p.publication-year }};'
                )
            else:
                query = (
                    'match $p isa scilit-paper; '
                    'fetch { "id": $p.id, "name": $p.name, "doi": $p.doi, "year": $p.publication-year };'
                )
            results = list(tx.query(query).resolve())

    papers = [{k: v for k, v in r.items() if v is not None} for r in results]
    print(json.dumps({
        "success": True,
        "papers": papers,
        "count": len(papers),
        "collection": args.collection if hasattr(args, "collection") else None,
    }, indent=2))


# =============================================================================
# SEMANTIC SEARCH + CLUSTERING COMMANDS
# =============================================================================

def _get_collection_papers(driver, collection_id: str) -> list[dict]:
    """Fetch all scilit-papers in a collection from TypeDB."""
    with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
        results = list(tx.query(
            f'match $c isa collection, has id "{collection_id}"; '
            f'(collection: $c, member: $p) isa collection-membership; '
            f'$p isa scilit-paper; '
            f'fetch {{ "id": $p.id, "name": $p.name, '
            f'"abstract-text": $p.abstract-text, '
            f'"doi": $p.doi, "year": $p.publication-year }};'
        ).resolve())
    return [{k: v for k, v in r.items() if v is not None} for r in results]


def cmd_embed(args):
    """Fetch papers from TypeDB, embed with Voyage AI, upsert into Qdrant."""
    try:
        from skillful_alhazen.utils.embeddings import embed_texts
        from skillful_alhazen.utils.vector_store import (
            ensure_collection, get_existing_paper_ids, get_qdrant_client, upsert_papers,
        )
    except ImportError as e:
        print(json.dumps({"success": False, "error": f"Missing dependency: {e}"}))
        sys.exit(1)

    if not VOYAGE_API_KEY:
        print(json.dumps({"success": False, "error": "VOYAGE_API_KEY not set"}))
        sys.exit(1)

    collection_id = args.collection
    print(f"Fetching papers for collection {collection_id}...", file=sys.stderr)

    with get_driver() as driver:
        papers = _get_collection_papers(driver, collection_id)

    if not papers:
        print(json.dumps({"success": False, "error": "No papers found in collection"}))
        sys.exit(1)

    print(f"Found {len(papers)} papers", file=sys.stderr)

    qdrant = get_qdrant_client()
    ensure_collection(qdrant)

    # Determine which papers need embedding
    all_ids = [p["id"] for p in papers]
    if args.reembed:
        already_in_qdrant = 0
        to_embed = papers
    else:
        existing_ids = get_existing_paper_ids(qdrant, all_ids)
        already_in_qdrant = len(existing_ids)
        to_embed = [p for p in papers if p["id"] not in existing_ids]

    if args.limit > 0:
        to_embed = to_embed[: args.limit]

    print(f"Embedding {len(to_embed)} papers ({already_in_qdrant} already in Qdrant)...", file=sys.stderr)

    if not to_embed:
        print(json.dumps({
            "success": True, "embedded": 0, "skipped": skipped, "collection_id": collection_id,
        }, indent=2))
        return

    # Build texts: title + abstract
    texts = [
        f"{p.get('name', '')}\n\n{p.get('abstract-text', '')}"
        for p in to_embed
    ]

    # Embed in batches (progress to stderr)
    from skillful_alhazen.utils.embeddings import VOYAGE_BATCH_SIZE
    all_vectors = []
    for i in range(0, len(texts), VOYAGE_BATCH_SIZE):
        batch_end = min(i + VOYAGE_BATCH_SIZE, len(texts))
        print(f"  Embedding {i + 1}-{batch_end} / {len(texts)}...", file=sys.stderr)
        batch_vectors = embed_texts(texts[i:batch_end], input_type="document")
        all_vectors.extend(batch_vectors)

    # Upsert to Qdrant
    points = [
        {
            "paper_id": p["id"],
            "vector": v,
            "title": p.get("name", ""),
            "collection_ids": [collection_id],
            "doi": p.get("doi", ""),
            "year": p.get("year"),
        }
        for p, v in zip(to_embed, all_vectors)
    ]
    upsert_papers(qdrant, points)

    print(json.dumps({
        "success": True,
        "embedded": len(to_embed),
        "skipped": already_in_qdrant,
        "collection_id": collection_id,
    }, indent=2))


def cmd_search_semantic(args):
    """Embed a query and return similar papers from Qdrant."""
    try:
        from skillful_alhazen.utils.embeddings import embed_texts
        from skillful_alhazen.utils.vector_store import get_qdrant_client, search_similar
    except ImportError as e:
        print(json.dumps({"success": False, "error": f"Missing dependency: {e}"}))
        sys.exit(1)

    if not VOYAGE_API_KEY:
        print(json.dumps({"success": False, "error": "VOYAGE_API_KEY not set"}))
        sys.exit(1)

    print(f"Embedding query: {args.query}", file=sys.stderr)
    query_vectors = embed_texts([args.query], input_type="query")
    query_vector = query_vectors[0]

    qdrant = get_qdrant_client()
    results = search_similar(
        qdrant,
        query_vector,
        collection_id=args.collection,
        limit=args.limit,
    )

    print(json.dumps({
        "success": True,
        "query": args.query,
        "collection": args.collection,
        "results": results,
    }, indent=2))


def cmd_cluster(args):
    """
    Cluster collection embeddings with UMAP + HDBSCAN and output representative titles.
    Use --dry-run to inspect clusters before writing tags.
    """
    try:
        import hdbscan
        import numpy as np
        import umap
        from skillful_alhazen.utils.vector_store import get_collection_vectors, get_qdrant_client
    except ImportError as e:
        print(json.dumps({"success": False, "error": f"Missing dependency: {e}"}))
        sys.exit(1)

    collection_id = args.collection
    print(f"Loading vectors for collection {collection_id}...", file=sys.stderr)

    qdrant = get_qdrant_client()
    points = get_collection_vectors(qdrant, collection_id)

    if not points:
        print(json.dumps({"success": False, "error": "No vectors found for collection"}))
        sys.exit(1)

    n = len(points)
    print(f"Reducing {n} papers with UMAP...", file=sys.stderr)

    vectors = np.array([p["vector"] for p in points], dtype=np.float32)

    # UMAP: reduce to 50 dims with cosine metric (natural for embeddings)
    reducer = umap.UMAP(
        n_components=50,
        n_neighbors=min(15, n - 1),
        min_dist=0.0,
        metric="cosine",
        random_state=42,
    )
    reduced = reducer.fit_transform(vectors)

    print(f"Clustering with HDBSCAN (min_cluster_size={args.min_cluster_size})...", file=sys.stderr)

    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=args.min_cluster_size,
        metric="euclidean",
    )
    labels = clusterer.fit_predict(reduced)

    unique_labels = sorted(set(labels))
    clusters = []

    for label in unique_labels:
        if label == -1:
            continue  # noise / unclustered
        mask = labels == label
        cluster_indices = np.where(mask)[0]
        cluster_vectors = reduced[cluster_indices]
        centroid = cluster_vectors.mean(axis=0)

        # Find 5 closest to centroid
        dists = np.linalg.norm(cluster_vectors - centroid, axis=1)
        closest_idx = np.argsort(dists)[:5]
        representative_papers = [
            {
                "paper_id": points[cluster_indices[i]]["paper_id"],
                "title": points[cluster_indices[i]]["title"],
                "doi": points[cluster_indices[i]].get("doi", ""),
            }
            for i in closest_idx
        ]

        clusters.append({
            "cluster_id": int(label),
            "size": int(mask.sum()),
            "representative_papers": representative_papers,
        })

    noise_count = int((labels == -1).sum())

    # If --labels provided and not dry-run: write keyword tags to TypeDB
    if not args.dry_run and args.labels:
        label_map = {}
        for entry in args.labels:
            parts = entry.split(":", 1)
            if len(parts) == 2:
                try:
                    label_map[int(parts[0])] = parts[1]
                except ValueError:
                    pass

        if label_map:
            print("Writing theme tags to TypeDB...", file=sys.stderr)
            with get_driver() as driver:
                for cluster in clusters:
                    cid = cluster["cluster_id"]
                    theme = label_map.get(cid)
                    if not theme:
                        continue
                    # Find all papers in this cluster
                    cluster_mask = labels == cid
                    cluster_paper_ids = [
                        points[i]["paper_id"] for i in np.where(cluster_mask)[0]
                    ]
                    theme_escaped = escape_string(theme)
                    with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
                        for pid in cluster_paper_ids:
                            try:
                                tx.query(
                                    f'match $p isa scilit-paper, has id "{pid}"; '
                                    f'insert $p has keyword "{theme_escaped}";'
                                ).resolve()
                            except Exception:
                                pass
                        tx.commit()
                    print(f"  Tagged {len(cluster_paper_ids)} papers with '{theme}'", file=sys.stderr)

    print(json.dumps({
        "success": True,
        "collection_id": collection_id,
        "total_papers": len(points),
        "clustered": len(points) - noise_count,
        "noise": noise_count,
        "num_clusters": len(clusters),
        "clusters": clusters,
    }, indent=2))


def cmd_plot_clusters(args):
    """
    Generate a 2D UMAP scatter plot of collection embeddings coloured by HDBSCAN cluster.
    Saves a PNG to --output (default: clusters.png).
    """
    try:
        import hdbscan
        import matplotlib.pyplot as plt
        import numpy as np
        import umap
        from skillful_alhazen.utils.vector_store import get_collection_vectors, get_qdrant_client
    except ImportError as e:
        print(json.dumps({"success": False, "error": f"Missing dependency: {e}"}))
        sys.exit(1)

    collection_id = args.collection
    output = args.output

    print(f"Loading vectors for collection {collection_id}...", file=sys.stderr)
    qdrant = get_qdrant_client()
    points = get_collection_vectors(qdrant, collection_id)

    if not points:
        print(json.dumps({"success": False, "error": "No vectors found for collection"}))
        sys.exit(1)

    n = len(points)
    vectors = np.array([p["vector"] for p in points], dtype=np.float32)
    titles = [p.get("title", "") for p in points]

    # Step 1: 50-dim UMAP for clustering
    print("UMAP 50-dim for clustering...", file=sys.stderr)
    reducer_50 = umap.UMAP(
        n_components=50,
        n_neighbors=min(15, n - 1),
        min_dist=0.0,
        metric="cosine",
        random_state=42,
    )
    reduced_50 = reducer_50.fit_transform(vectors)

    # Step 2: HDBSCAN labels
    print(f"HDBSCAN (min_cluster_size={args.min_cluster_size})...", file=sys.stderr)
    clusterer = hdbscan.HDBSCAN(min_cluster_size=args.min_cluster_size, metric="euclidean")
    labels = clusterer.fit_predict(reduced_50)

    # Step 3: 2D UMAP for visualisation (reuse 50-dim as input for speed + consistency)
    print("UMAP 2-dim for plot...", file=sys.stderr)
    reducer_2d = umap.UMAP(
        n_components=2,
        n_neighbors=min(15, n - 1),
        min_dist=0.1,
        metric="euclidean",
        random_state=42,
    )
    xy = reducer_2d.fit_transform(reduced_50)

    # Build colour map: noise = light grey, each cluster a distinct colour
    unique_labels = sorted(set(labels))
    cluster_labels = [l for l in unique_labels if l != -1]
    cmap = plt.colormaps["tab20"].resampled(max(len(cluster_labels), 1))
    colour_map = {l: cmap(i % 20) for i, l in enumerate(cluster_labels)}
    colour_map[-1] = (0.8, 0.8, 0.8, 0.3)  # noise: translucent grey

    colours = [colour_map[l] for l in labels]

    # Plot
    fig, ax = plt.subplots(figsize=(14, 10))
    ax.scatter(xy[:, 0], xy[:, 1], c=colours, s=6, linewidths=0)

    # Parse --labels map
    label_map = {}
    if args.labels:
        for entry in args.labels:
            parts = entry.split(":", 1)
            if len(parts) == 2:
                try:
                    label_map[int(parts[0])] = parts[1]
                except ValueError:
                    pass

    # Label each cluster at its centroid
    for label in cluster_labels:
        mask = labels == label
        cx, cy = xy[mask, 0].mean(), xy[mask, 1].mean()
        size = mask.sum()
        theme = label_map.get(label)
        text = f"{theme}\n(C{label}, n={size})" if theme else f"C{label} (n={size})"
        ax.annotate(
            text,
            (cx, cy),
            fontsize=7,
            ha="center",
            va="center",
            bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.75, lw=0),
        )

    noise_count = (labels == -1).sum()
    clustered = n - noise_count
    ax.set_title(
        f"MED13 corpus — {n} papers, {len(cluster_labels)} clusters, "
        f"{clustered} assigned ({noise_count} noise)\n"
        f"UMAP(cosine→50d) + HDBSCAN(min_size={args.min_cluster_size})",
        fontsize=11,
    )
    ax.set_xlabel("UMAP 1")
    ax.set_ylabel("UMAP 2")
    ax.axis("off")

    plt.tight_layout()
    plt.savefig(output, dpi=150, bbox_inches="tight")
    plt.close()

    print(json.dumps({
        "success": True,
        "output": output,
        "num_clusters": len(cluster_labels),
        "clustered": int(clustered),
        "noise": int(noise_count),
        "total": n,
    }, indent=2))


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Literature CLI - multi-source scientific paper search and ingestion"
    )
    subparsers = parser.add_subparsers(dest="command")

    # search
    p = subparsers.add_parser("search", help="Search a literature source")
    p.add_argument("--source", required=True,
                   choices=["pubmed", "openalex", "biorxiv", "medrxiv"],
                   help="Literature source to search")
    p.add_argument("--query", required=True, help="Search query")
    p.add_argument("--collection", help="Collection ID to add results to")
    p.add_argument("--max-results", type=int, default=20, help="Max results (default: 20)")

    # ingest
    p = subparsers.add_parser("ingest", help="Fetch and store a paper by DOI")
    p.add_argument("--doi", required=True, help="DOI (with or without https://doi.org/ prefix)")
    p.add_argument("--collection", help="Collection ID to add to")

    # show
    p = subparsers.add_parser("show", help="Show a paper for sensemaking")
    p.add_argument("--id", required=True, help="Paper ID (scilit-paper-...)")

    # list
    p = subparsers.add_parser("list", help="List papers in the knowledge graph")
    p.add_argument("--collection", help="Filter by collection ID")

    # embed
    p = subparsers.add_parser("embed", help="Embed collection papers with Voyage AI into Qdrant")
    p.add_argument("--collection", required=True, help="Collection ID to embed")
    p.add_argument("--reembed", action="store_true",
                   help="Re-embed even if paper already exists in Qdrant")
    p.add_argument("--limit", type=int, default=0,
                   help="Max papers to embed (0 = all, default: 0)")

    # search-semantic
    p = subparsers.add_parser("search-semantic", help="Semantic similarity search via Qdrant")
    p.add_argument("--query", required=True, help="Natural language query")
    p.add_argument("--collection", help="Filter results to this collection ID")
    p.add_argument("--limit", type=int, default=10, help="Max results (default: 10)")

    # plot-clusters
    p = subparsers.add_parser("plot-clusters", help="2D UMAP scatter plot coloured by cluster")
    p.add_argument("--collection", required=True, help="Collection ID")
    p.add_argument("--min-cluster-size", type=int, default=10,
                   help="HDBSCAN min_cluster_size (default: 10)")
    p.add_argument("--output", default="clusters.png", help="Output PNG path (default: clusters.png)")
    p.add_argument("--labels", nargs="*",
                   help="Theme labels: 0:theme-a 1:theme-b ...")

    # cluster
    p = subparsers.add_parser("cluster", help="HDBSCAN clustering of collection embeddings")
    p.add_argument("--collection", required=True, help="Collection ID to cluster")
    p.add_argument("--min-cluster-size", type=int, default=15,
                   help="HDBSCAN min_cluster_size (default: 15)")
    p.add_argument("--dry-run", action="store_true",
                   help="Output cluster info without writing tags to TypeDB")
    p.add_argument("--labels", nargs="*",
                   help="Theme labels for clusters: 0:theme-name 1:other-theme ...")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    SEMANTIC_COMMANDS = {"embed", "search-semantic", "cluster"}
    if args.command not in SEMANTIC_COMMANDS:
        if not TYPEDB_AVAILABLE:
            print(json.dumps({"success": False, "error": "typedb-driver not installed"}))
            sys.exit(1)
        if not REQUESTS_AVAILABLE:
            print(json.dumps({"success": False,
                              "error": "requests not installed. Run: uv add requests"}))
            sys.exit(1)

    commands = {
        "search": cmd_search,
        "ingest": cmd_ingest,
        "show": cmd_show,
        "list": cmd_list,
        "embed": cmd_embed,
        "search-semantic": cmd_search_semantic,
        "cluster": cmd_cluster,
        "plot-clusters": cmd_plot_clusters,
    }

    try:
        commands[args.command](args)
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
