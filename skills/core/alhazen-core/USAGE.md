# Alhazen Core — Usage Reference

## Commands

### `init`

Idempotent setup: starts the TypeDB Docker container, creates the `alhazen_notebook` database, and loads the base schema.

```bash
uv run --project <skill-path> python <skill-path>/alhazen_core.py init
```

**Expected output:**
```json
{
  "success": true,
  "typedb": "running",
  "database": "alhazen_notebook",
  "database_created": true,
  "schema": "loaded",
  "message": "Alhazen core ready."
}
```

Re-running `init` is safe — it skips steps that are already done.

**Auto-schema detection:** If a `schema.tql` file exists in the same directory as `alhazen_core.py`, `init` loads it automatically after the base schema. The output will include `"extra_schema": "loaded"` and an updated message. This is used by self-contained plugin bundles (e.g. `plugins/jobhunt/`) so a single SessionStart hook initializes both schemas without a separate `init-schema` step.

### `status`

Check whether Docker, the TypeDB container, and the database are ready.

```bash
uv run --project <skill-path> python <skill-path>/alhazen_core.py status
```

### `reset`

Drop and recreate the database, reloading the base schema. **Destroys all data.**

```bash
uv run --project <skill-path> python <skill-path>/alhazen_core.py reset --yes
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TYPEDB_HOST` | `localhost` | TypeDB server host |
| `TYPEDB_PORT` | `1729` | TypeDB server port |
| `TYPEDB_DATABASE` | `alhazen_notebook` | Database name |
| `TYPEDB_USERNAME` | `admin` | TypeDB username |
| `TYPEDB_PASSWORD` | `password` | TypeDB password |

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `Docker is not running` | Start Docker Desktop (macOS) or `sudo systemctl start docker` |
| Container fails to start in 60s | `docker logs alhazen-typedb` — increase Docker memory in Desktop settings |
| Port 1729 already in use | `docker ps -a \| grep 1729` then `docker stop <id>` |
| Schema error `[SYR1]` | Run `reset --yes` to start fresh |

## After Init

After `init` succeeds, load each domain skill's schema:

```bash
# Example for jobhunt skill
uv run --project <jobhunt-path> python <jobhunt-path>/jobhunt.py init-schema

# Example for scientific-literature skill
uv run --project <scilit-path> python <scilit-path>/scientific_literature.py init-schema
```
