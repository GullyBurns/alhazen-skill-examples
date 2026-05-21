#!/usr/bin/env python3
"""
Alhazen Core — TypeDB infrastructure setup for Alhazen skills.

Starts the TypeDB Docker container, creates the database, and loads the base schema.
Run this once before installing any other Alhazen skill.

Usage:
    python alhazen_core.py init                        # Start TypeDB, create DB, load base schema
    python alhazen_core.py load-schema FILE.tql         # Load additional schema into existing DB
    python alhazen_core.py status                       # Check TypeDB container and database state
    python alhazen_core.py reset                        # Drop and recreate the database (WARNING: destroys data)

Environment:
    TYPEDB_HOST         TypeDB host (default: localhost)
    TYPEDB_PORT         TypeDB port (default: 1729)
    TYPEDB_DATABASE     Database name (default: alhazen_notebook)
    TYPEDB_USERNAME     TypeDB username (default: admin)
    TYPEDB_PASSWORD     TypeDB password (default: password)
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

TYPEDB_HOST = os.getenv("TYPEDB_HOST", "localhost")
TYPEDB_PORT = int(os.getenv("TYPEDB_PORT", "1729"))
TYPEDB_DATABASE = os.getenv("TYPEDB_DATABASE", "alhazen_notebook")
TYPEDB_USERNAME = os.getenv("TYPEDB_USERNAME", "admin")
TYPEDB_PASSWORD = os.getenv("TYPEDB_PASSWORD", "password")

TYPEDB_IMAGE = "typedb/typedb:3.8.0"
TYPEDB_CONTAINER = "alhazen-typedb"

SCHEMA_FILE = Path(__file__).parent / "alhazen_notebook.tql"


def _docker(*args, check=True, capture=True):
    """Run a docker command, return CompletedProcess."""
    cmd = ["docker"] + list(args)
    return subprocess.run(cmd, capture_output=capture, text=True, check=check)


def _is_docker_running():
    try:
        _docker("info")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def _container_status():
    """Return container status string or '' if not found."""
    try:
        r = _docker("inspect", "--format", "{{.State.Status}}", TYPEDB_CONTAINER)
        return r.stdout.strip()
    except subprocess.CalledProcessError:
        return ""


def _start_typedb():
    """Start the TypeDB container, pulling image if needed. Returns True on success."""
    status = _container_status()
    if status == "running":
        return True
    if status == "exited":
        _docker("start", TYPEDB_CONTAINER)
    else:
        # Container doesn't exist — create it
        _docker(
            "run", "-d",
            "--name", TYPEDB_CONTAINER,
            "-p", f"{TYPEDB_PORT}:1729",
            TYPEDB_IMAGE,
        )

    # Wait for TypeDB to become ready (up to 60s)
    for _ in range(60):
        time.sleep(1)
        try:
            from typedb.driver import Credentials, DriverOptions, TypeDB
            driver = TypeDB.driver(
                f"{TYPEDB_HOST}:{TYPEDB_PORT}",
                Credentials(TYPEDB_USERNAME, TYPEDB_PASSWORD),
                DriverOptions(is_tls_enabled=False),
            )
            driver.close()
            return True
        except Exception:
            pass
    return False


def _get_driver():
    try:
        from typedb.driver import Credentials, DriverOptions, TypeDB
        return TypeDB.driver(
            f"{TYPEDB_HOST}:{TYPEDB_PORT}",
            Credentials(TYPEDB_USERNAME, TYPEDB_PASSWORD),
            DriverOptions(is_tls_enabled=False),
        )
    except ImportError:
        print(
            json.dumps({"success": False, "error": "typedb-driver not installed. Run: uv sync"}),
            file=sys.stderr,
        )
        sys.exit(1)


def _database_exists(driver):
    try:
        return driver.databases.contains(TYPEDB_DATABASE)
    except Exception:
        return False


def _create_database(driver):
    """Create the database if it doesn't exist."""
    if not _database_exists(driver):
        driver.databases.create(TYPEDB_DATABASE)
        return True
    return False


def _load_schema(driver):
    """Load alhazen_notebook.tql into the database."""
    from typedb.driver import TransactionType
    schema_text = SCHEMA_FILE.read_text(encoding="utf-8")
    with driver.transaction(TYPEDB_DATABASE, TransactionType.SCHEMA) as tx:
        tx.query(schema_text).resolve()
        tx.commit()


def _load_extra_schema(driver, schema_path):
    """Load an additional schema file into the database."""
    from typedb.driver import TransactionType
    schema_text = schema_path.read_text(encoding="utf-8")
    with driver.transaction(TYPEDB_DATABASE, TransactionType.SCHEMA) as tx:
        tx.query(schema_text).resolve()
        tx.commit()


def cmd_init(args):
    """Start TypeDB, create database, load base schema."""
    result = {"step": "", "success": False}

    # Step 1: Docker
    result["step"] = "docker"
    if not _is_docker_running():
        print(json.dumps({"success": False, "error": "Docker is not running. Start Docker Desktop (macOS) or `sudo systemctl start docker` (Linux)."}))
        sys.exit(1)

    # Step 2: TypeDB container
    result["step"] = "typedb-container"
    if not _start_typedb():
        print(json.dumps({"success": False, "error": f"TypeDB container failed to start within 60s. Check: docker logs {TYPEDB_CONTAINER}"}))
        sys.exit(1)

    # Step 3: Database
    result["step"] = "database"
    with _get_driver() as driver:
        created = _create_database(driver)

        # Step 4: Base schema
        result["step"] = "schema"
        try:
            _load_schema(driver)
            schema_result = "loaded"
        except Exception as e:
            # Schema may already be loaded — that's fine
            schema_result = f"already-loaded (or error: {e})"

        # Step 5: Load extra schemas passed via --extra-schema
        extra_results = []
        for extra in (args.extra_schema or []):
            extra_path = Path(extra)
            if not extra_path.exists():
                extra_results.append({"file": str(extra_path), "result": "not-found"})
                continue
            try:
                _load_extra_schema(driver, extra_path)
                extra_results.append({"file": str(extra_path), "result": "loaded"})
            except Exception as e:
                extra_results.append({"file": str(extra_path), "result": f"already-loaded (or error: {e})"})

    output = {
        "success": True,
        "typedb": "running",
        "database": TYPEDB_DATABASE,
        "database_created": created,
        "schema": schema_result,
        "message": "Alhazen core ready.",
    }
    if extra_results:
        output["extra_schemas"] = extra_results
    print(json.dumps(output))


def cmd_status(args):
    """Check TypeDB container and database state."""
    docker_ok = _is_docker_running()
    container_status = _container_status() if docker_ok else "docker-not-running"

    typedb_reachable = False
    db_exists = False
    if container_status == "running":
        try:
            with _get_driver() as driver:
                typedb_reachable = True
                db_exists = _database_exists(driver)
        except Exception:
            pass

    print(json.dumps({
        "success": True,
        "docker": "running" if docker_ok else "not-running",
        "container": container_status,
        "typedb_reachable": typedb_reachable,
        "database": TYPEDB_DATABASE,
        "database_exists": db_exists,
    }))


def cmd_load_schema(args):
    """Load an additional schema file into the existing database."""
    schema_path = Path(args.schema_file)
    if not schema_path.exists():
        print(json.dumps({"success": False, "error": f"Schema file not found: {schema_path}"}))
        sys.exit(1)

    with _get_driver() as driver:
        if not _database_exists(driver):
            print(json.dumps({"success": False, "error": f"Database '{TYPEDB_DATABASE}' does not exist. Run 'init' first."}))
            sys.exit(1)

        try:
            _load_extra_schema(driver, schema_path)
            result = "loaded"
        except Exception as e:
            result = f"already-loaded (or error: {e})"

    print(json.dumps({
        "success": True,
        "database": TYPEDB_DATABASE,
        "schema_file": str(schema_path),
        "schema": result,
    }))


def cmd_reset(args):
    """Drop and recreate the database. WARNING: destroys all data."""
    if not args.yes:
        print(json.dumps({"success": False, "error": "Pass --yes to confirm database reset. This destroys ALL data."}))
        sys.exit(1)

    with _get_driver() as driver:
        if _database_exists(driver):
            driver.databases.get(TYPEDB_DATABASE).delete()
        driver.databases.create(TYPEDB_DATABASE)
        _load_schema(driver)

    print(json.dumps({
        "success": True,
        "database": TYPEDB_DATABASE,
        "schema": "loaded",
        "message": "Database reset. Re-run each skill's init-schema command to reload domain schemas.",
    }))


def main():
    parser = argparse.ArgumentParser(description="Alhazen Core — TypeDB infrastructure setup")
    sub = parser.add_subparsers(dest="command", required=True)

    init_p = sub.add_parser("init", help="Start TypeDB, create database, load base schema")
    init_p.add_argument("--extra-schema", nargs="*", help="Additional .tql schema files to load after base schema")

    load_p = sub.add_parser("load-schema", help="Load a schema file into the existing database")
    load_p.add_argument("schema_file", help="Path to the .tql schema file")

    sub.add_parser("status", help="Check TypeDB container and database state")

    reset_p = sub.add_parser("reset", help="Drop and recreate the database (destroys data)")
    reset_p.add_argument("--yes", action="store_true", help="Confirm destructive reset")

    args = parser.parse_args()
    dispatch = {"init": cmd_init, "load-schema": cmd_load_schema, "status": cmd_status, "reset": cmd_reset}
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
