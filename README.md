# Eco Impact Dashboard

Monorepo for a full-stack **environmental impact dashboard** focused on AI workloads: **energy**, **grid CO₂**, **water**, and **model comparisons**. The UI is **Next.js 15**; the API is **FastAPI** with **PostgreSQL / TimescaleDB** and **Redis**.

---

## Architecture

### System overview

```mermaid
flowchart LR
  subgraph Browser
    UI[Next.js app]
  end
  subgraph NextServer[Next.js server]
    BFF[Route handlers /api/*]
  end
  subgraph API[FastAPI :8000]
    REST[REST routers]
    SVC[Services: impact, carbon, cache]
  end
  subgraph Data
    PG[(TimescaleDB)]
    RD[(Redis)]
  end
  subgraph External[Optional APIs]
    EM[Electricity Maps]
    WT[WattTime]
  end
  UI --> BFF
  BFF --> REST
  REST --> SVC
  SVC --> PG
  SVC --> RD
  SVC --> EM
  SVC --> WT
```

### Request path (typical dashboard load)

```mermaid
sequenceDiagram
  participant B as Browser
  participant N as Next.js BFF
  participant F as FastAPI
  participant D as TimescaleDB
  participant R as Redis
  B->>N: GET /api/dashboard/metrics
  N->>F: GET /api/dashboard/metrics
  F->>D: SQL aggregates / reads
  F->>R: Optional cache reads
  F-->>N: JSON
  N-->>B: JSON
```

### Repository layout

| Path | Role |
|------|------|
| `apps/web` | Next.js 15 (App Router), React 19, Tailwind 4, shadcn/ui, Recharts / ECharts / Leaflet |
| `apps/api` | FastAPI, SQLAlchemy 2 async, Alembic, Pydantic v2, httpx, optional Prefect flows |
| `packages/shared-types` | Shared TypeScript types (`workspace:^` from web) |

---

## Tech stack

| Layer | Technologies |
|-------|----------------|
| Frontend | Next.js 15, React 19, TypeScript 5, TanStack Query, Tailwind CSS 4 |
| Backend | Python 3.12+, FastAPI, Uvicorn, SQLAlchemy, asyncpg |
| Data | TimescaleDB (hypertables: `carbon_intensity_readings`, `energy_estimates`), Redis |
| Tooling | Turborepo, pnpm 9+, Alembic |

---

## Prerequisites

- **Node.js** 20+
- **pnpm** 9+ (`corepack enable pnpm`)
- **Python** 3.12+
- **Docker** + Docker Compose (local DB + Redis)

---

## Quick start

### 1. Install dependencies

```bash
git clone <your-fork-url> eco-impact-dashboard
cd eco-impact-dashboard
pnpm install
```

### 2. Infrastructure

```bash
docker compose up -d
```

- **TimescaleDB** → `localhost:5432`, database `eco_dashboard`, user `postgres`, password `dev_password` (see `docker-compose.yml`)
- **Redis** → `localhost:6379`

### 3. Environment

Copy [.env.example](.env.example) to `.env` at the repo root. For FastAPI, mirror the same variables in `apps/api/.env` (or symlink). For Next server routes, set at least:

- `API_URL=http://localhost:8000`
- `NEXT_PUBLIC_API_URL=http://localhost:8000` (if you use it in server config)

Never commit real `.env` files (they are gitignored).

### 4. Database migrations & seed

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
pip install -e ".[dev]"     # optional: Ruff for linting
alembic upgrade head
python seed.py
python fetch_initial_data.py   # optional: needs Electricity Maps API key
```

### 5. Run development servers

From the **monorepo root**:

```bash
pnpm dev
```

- **Web:** http://localhost:3000  
- **API:** http://localhost:8000 — health: http://localhost:8000/health  

`pnpm dev` runs Turbo `dev` tasks: shared-types watch, API (Uvicorn), and Next dev.

**Alternative:** automated bootstrap (Docker + migrate + seed + optional fetch):

```bash
chmod +x setup.sh
./setup.sh
```

---

## npm / pnpm scripts

| Command | Description |
|---------|-------------|
| `pnpm dev` | Turbo: web + api + shared-types in watch mode |
| `pnpm build` | Production build (Next + shared types) |
| `pnpm lint` | Lint across packages |

`apps/api/package.json` also defines `db:upgrade`, `db:seed`, etc.

---

## API surface (high level)

- **`/api/dashboard/*`** — Metrics, energy timeline, carbon by region/history, training/split heuristics, best times
- **`/api/impact/*`** — Per-model estimates, comparison, catalog
- **`/api/carbon/*`** — Carbon helpers / regions
- **`/api/datacenters`**, **`/api/sustainability/reports`**, **`/api/gpu/benchmarks`** — Catalog data
- **`/health`** — Liveness

CORS defaults target `http://localhost:3000` (`apps/api/app/core/config.py`).

---

## Troubleshooting

| Issue | What to check |
|------|----------------|
| API **connection refused** to Postgres | `docker compose ps`; use `localhost` in `DATABASE_URL` when the API runs on the host (not the Docker service name `postgres`). |
| **pnpm** workspace errors | Run `pnpm install` from the **repo root**, not only `apps/web`. |
| **Nested `.git` in `apps/web`** | Remove it if you want a single repository at the monorepo root. |
| Next **lockfile / turbopack root** | `apps/web/next.config.ts` may set `turbopack.root` to the monorepo root. |

---

## Before pushing to GitHub

- Confirm **no secrets** in the repo (only `.env.example` with empty or dummy values).
- Add a **LICENSE** if the project is public.
- Run `pnpm build` and smoke-test `pnpm dev` locally.

---

## Contributing

Issues and PRs are welcome. Keep API and web changes aligned with shared types in `packages/shared-types` when you touch request/response shapes.
