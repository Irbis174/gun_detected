# Backend

## PostgreSQL

Start PostgreSQL from the repository root:

```powershell
docker compose up -d postgres
```

Use this connection string for local development:

```powershell
$env:DATABASE_URL = "postgresql+psycopg://diploma:diploma@localhost:5433/diploma"
```

For a demo build, the backend can create missing tables on startup:

```powershell
$env:AUTO_CREATE_TABLES = "1"
```

For a production-like deployment, use Alembic migrations instead:

```powershell
cd packages/backend
uv run alembic upgrade head
```

Detection frames are stored on disk, while PostgreSQL stores metadata and
the `frame_path` value.
