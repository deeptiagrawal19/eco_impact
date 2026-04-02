# Eco Impact API

FastAPI service for the eco-impact dashboard. Run from this directory:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Database (TimescaleDB + Alembic)

Start Postgres/Timescale from the monorepo root (`docker compose up -d`), then from **`apps/api`**:

```bash
pip install -e .
alembic upgrade head
PYTHONPATH=. python seed.py
```

Or via pnpm from the monorepo root: `pnpm --filter api db:upgrade` and `pnpm --filter api db:seed`.

Schema includes hypertables `carbon_intensity_readings` and `energy_estimates` (`create_hypertable(..., 'time')`). Migrations live in `alembic/versions/`.

## Carbon ETL (Prefect)

Ingestion flow (Electricity Maps → WattTime fallback → TimescaleDB):

```bash
# from apps/api with venv + deps installed
PYTHONPATH=. python pipelines/flows/carbon_intensity.py
```

Schedule every 15 minutes via Prefect Cloud / Server deployment, or cron wrapping the command above.

HTTP: `GET /api/carbon/latest|history|regions|comparison`. Requires Redis and API keys in `.env` for live vendor calls.
