#!/usr/bin/env python3
"""Compute 2D embedding map of job opportunities for the dashboard.

Reads opportunity notes from TypeDB, embeds via Voyage AI, stores in Qdrant,
and runs PyMDE to produce 2D coordinates for visualization.

Usage:
    # Compute embeddings and store in Qdrant (run after sensemaking)
    uv run python local_skills/jobhunt/embedding_map.py embed

    # Get 2D map coordinates (fast — reads from Qdrant, runs PyMDE)
    uv run python local_skills/jobhunt/embedding_map.py map [--exclude id1 id2 ...]

    # Both: embed then map
    uv run python local_skills/jobhunt/embedding_map.py embed-and-map
"""
import argparse
import json
import os
import sys

TYPEDB_HOST = os.getenv("TYPEDB_HOST", "localhost")
TYPEDB_PORT = int(os.getenv("TYPEDB_PORT", "1729"))
TYPEDB_DATABASE = os.getenv("TYPEDB_DATABASE", "alhazen_notebook")
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
COLLECTION = "jobhunt-opportunities"
VECTOR_DIM = 1024  # voyage-4-large


def get_typedb_driver():
    from typedb.driver import Credentials, DriverOptions, TypeDB
    return TypeDB.driver(
        f"{TYPEDB_HOST}:{TYPEDB_PORT}",
        Credentials("admin", "password"),
        DriverOptions(is_tls_enabled=False),
    )


def get_qdrant_client():
    from qdrant_client import QdrantClient
    return QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)


def ensure_collection():
    """Create Qdrant collection if it doesn't exist."""
    from qdrant_client.models import Distance, VectorParams
    client = get_qdrant_client()
    collections = [c.name for c in client.get_collections().collections]
    if COLLECTION not in collections:
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
        )
        print(f"Created Qdrant collection: {COLLECTION}", file=sys.stderr)
    return client


def fetch_opportunities():
    """Fetch all opportunities with their sensemaking notes from TypeDB."""
    from typedb.driver import TransactionType

    driver = get_typedb_driver()
    opportunities = []

    with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
        # Get all opportunity subtypes
        for otype in ["jobhunt-position", "jobhunt-engagement", "jobhunt-venture", "jobhunt-lead"]:
            type_label = otype.replace("jobhunt-", "")
            opps = list(tx.query(f'''match $o isa {otype}, has id $id, has name $n;
                fetch {{ "id": $id, "name": $n }};''').resolve())

            for opp in opps:
                oid = opp["id"]
                oname = opp["name"]

                # Get short-name, priority, status
                extras = {}
                for attr in ["short-name", "priority-level"]:
                    try:
                        r = list(tx.query(f'''match $o isa {otype}, has id "{oid}", has {attr} $v;
                            fetch {{ "v": $v }};''').resolve())
                        if r:
                            extras[attr] = r[0]["v"]
                    except:
                        pass

                # Get application status (from note)
                try:
                    status_r = list(tx.query(f'''match
                        $o isa {otype}, has id "{oid}";
                        (note: $n, subject: $o) isa aboutness;
                        $n isa jobhunt-application-note, has application-status $s;
                    fetch {{ "status": $s }};''').resolve())
                    if status_r:
                        extras["status"] = status_r[0]["status"]
                except:
                    pass

                # Get company
                company = None
                try:
                    for rel in ["position-at-company", "opportunity-at-organization"]:
                        role = "employer" if "position" in rel else "organization"
                        co_r = list(tx.query(f'''match
                            $o isa {otype}, has id "{oid}";
                            ({rel.split("-")[0]}: $o, {role}: $c) isa {rel};
                        fetch {{ "company": $c.name }};''').resolve())
                        if co_r:
                            company = co_r[0]["company"]
                            break
                except:
                    pass

                # Get all sensemaking notes (research, fit-analysis, strategy, general)
                notes_text = []
                for ntype in ["jobhunt-research-note", "jobhunt-fit-analysis-note",
                              "jobhunt-strategy-note", "jobhunt-skill-gap-note", "note"]:
                    try:
                        notes = list(tx.query(f'''match
                            $o isa {otype}, has id "{oid}";
                            (note: $n, subject: $o) isa aboutness;
                            $n isa {ntype}, has content $c;
                        fetch {{ "content": $c }};''').resolve())
                        for n in notes:
                            if n.get("content"):
                                notes_text.append(n["content"])
                    except:
                        pass

                # Build the text to embed
                embed_text = f"Title: {oname}\n"
                if company:
                    embed_text += f"Company: {company}\n"
                embed_text += f"Type: {type_label}\n"
                if notes_text:
                    embed_text += "\n".join(notes_text)
                else:
                    embed_text += f"No sensemaking notes yet for this {type_label}."

                opportunities.append({
                    "id": oid,
                    "name": oname,
                    "short_name": extras.get("short-name", oname[:30]),
                    "type": type_label,
                    "status": extras.get("status"),
                    "priority": extras.get("priority-level"),
                    "company": company,
                    "text": embed_text,
                })

    driver.close()
    return opportunities


def cmd_embed(args):
    """Compute embeddings and store in Qdrant."""
    from skillful_alhazen.utils.embeddings import embed_texts
    from qdrant_client.models import PointStruct

    print("Fetching opportunities from TypeDB...", file=sys.stderr)
    opportunities = fetch_opportunities()
    print(f"Found {len(opportunities)} opportunities", file=sys.stderr)

    if not opportunities:
        print(json.dumps({"success": True, "count": 0}))
        return

    # Compute embeddings
    texts = [o["text"] for o in opportunities]
    print(f"Embedding {len(texts)} texts via Voyage AI...", file=sys.stderr)
    embeddings = embed_texts(texts, input_type="document")
    print(f"Got {len(embeddings)} embeddings", file=sys.stderr)

    # Store in Qdrant
    client = ensure_collection()
    points = []
    for i, (opp, emb) in enumerate(zip(opportunities, embeddings)):
        points.append(PointStruct(
            id=i,
            vector=emb,
            payload={
                "opp_id": opp["id"],
                "name": opp["name"],
                "short_name": opp["short_name"],
                "type": opp["type"],
                "status": opp["status"],
                "priority": opp["priority"],
                "company": opp["company"],
            },
        ))

    # Upsert (recreate collection to avoid stale points)
    from qdrant_client.models import Distance, VectorParams
    try:
        client.delete_collection(COLLECTION)
    except:
        pass
    client.create_collection(
        collection_name=COLLECTION,
        vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
    )
    client.upsert(collection_name=COLLECTION, points=points)
    print(f"Stored {len(points)} embeddings in Qdrant collection '{COLLECTION}'", file=sys.stderr)

    print(json.dumps({"success": True, "count": len(points)}))


def cmd_map(args):
    """Get 2D map coordinates from stored embeddings."""
    import numpy as np

    client = get_qdrant_client()

    # Fetch all points from Qdrant
    points = client.scroll(collection_name=COLLECTION, limit=10000, with_vectors=True)[0]

    if not points:
        print(json.dumps({"success": True, "items": [], "count": 0}))
        return

    # Apply exclusions
    exclude_set = set(args.exclude or [])
    filtered = [p for p in points if p.payload["opp_id"] not in exclude_set]

    if len(filtered) < 3:
        # Too few points for PyMDE — return as-is with random positions
        items = []
        for i, p in enumerate(filtered):
            items.append({
                **p.payload,
                "id": p.payload["opp_id"],
                "x": float(i),
                "y": 0.0,
            })
        print(json.dumps({"success": True, "items": items, "count": len(items)}))
        return

    # Extract vectors and run PyMDE
    import pymde
    import torch

    vectors = np.array([p.vector for p in filtered])
    tensor = torch.FloatTensor(vectors)

    mde = pymde.preserve_neighbors(tensor, embedding_dim=2, constraint=pymde.Standardized())
    embedding_2d = mde.embed().cpu().numpy()

    # Build output
    items = []
    for i, p in enumerate(filtered):
        items.append({
            **p.payload,
            "id": p.payload["opp_id"],
            "x": float(embedding_2d[i, 0]),
            "y": float(embedding_2d[i, 1]),
        })

    print(json.dumps({"success": True, "items": items, "count": len(items)}, default=str))


def cmd_embed_and_map(args):
    """Embed then map in one shot."""
    cmd_embed(args)
    cmd_map(args)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Jobhunt opportunity embedding map")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("embed", help="Compute embeddings and store in Qdrant")

    p_map = sub.add_parser("map", help="Get 2D map coordinates")
    p_map.add_argument("--exclude", nargs="*", help="Opportunity IDs to exclude")

    sub.add_parser("embed-and-map", help="Embed then map")

    args = parser.parse_args()
    if args.command == "embed":
        cmd_embed(args)
    elif args.command == "map":
        cmd_map(args)
    elif args.command == "embed-and-map":
        cmd_embed_and_map(args)
    else:
        parser.print_help()
