<!-- refreshed: 2026-07-17 -->
---
last_mapped_commit: 65e8aea3129b111ef8f8a20fcb3b4d218c70cbde
---
# Technology Stack

**Analysis Date:** 2026-07-17

## Languages

**Primary:**
- Python 3.12 (declared in `pyproject.toml`; CI uses 3.12) — backend API, game engine, migrations, seed tooling
- TypeScript ~6.0 / ES2023 — frontend SPA (`frontend/src/**`)

**Secondary:**
- SQL (Alembic migrations, SQLite PRAGMA bootstrap) — schema in `src/migrations/`, light migrate in `src/main.py`
- CSS / Tailwind utility classes — UI styling via `frontend/src/index.css`, `frontend/src/App.css`, `frontend/tailwind.config.js`
- Batch (Windows) — launcher `run_game.bat`

**Runtime note:** Local `venv/pyvenv.cfg` may pin Python 3.11.x even though `pyproject.toml` requires `^3.12`. Prefer 3.12 to match CI (`.github/workflows/ci.yml`).

## Runtime

**Environment:**
- Backend: CPython via project `venv/` (Windows Scripts: `uvicorn`, `pytest`, `alembic`)
- Frontend: Node.js 22 (CI); Vite dev server on port 5173
- Backend ASGI: Uvicorn serving `src.main:app` on port 8000

**Package Manager:**
- Backend: Poetry declared in `pyproject.toml` (`poetry-core` build backend) — **no `poetry.lock` committed**; local/CI install is effectively **pip** into `venv/`
- Frontend: **npm** with lockfile `frontend/package-lock.json` (lockfileVersion 3)
- Lockfile backend: missing (`poetry.lock` / `requirements.txt` not present)
- Lockfile frontend: present (`frontend/package-lock.json`)

## Frameworks

**Core:**
- FastAPI ^0.111 — HTTP API + OpenAPI (`src/main.py`, `src/api/routes/*`)
- SQLAlchemy 2.x async (`sqlalchemy[asyncio]`) — ORM + sessions (`src/core/database.py`, `src/models/*`)
- Pydantic v2 + pydantic-settings — request/response models and env config (`src/api/schemas.py`, `src/core/config.py`)
- React 19 + React DOM 19 — UI (`frontend/src/App.tsx`, screens under `frontend/src/screens/`)
- Zustand ^5 — client game state (`frontend/src/store/useGameStore.ts`)
- Vite ^8 + `@vitejs/plugin-react` — bundler/dev server (`frontend/vite.config.ts`)
- Tailwind CSS ^3.4 + PostCSS + Autoprefixer — design system (`frontend/tailwind.config.js`, `frontend/postcss.config.js`)

**Testing:**
- pytest ^8.2 + pytest-asyncio ^0.23 — backend (`tests/`, config in `pyproject.toml` `[tool.pytest.ini_options]`, `asyncio_mode = auto`)
- httpx ^0.27 — ASGI integration client in tests (`tests/conftest.py`)
- Vitest ^3.2 — frontend unit tests (`frontend/vitest.config.ts`, `frontend/src/lib/*.test.ts`)

**Build/Dev:**
- Uvicorn[standard] ^0.30 — ASGI server
- Alembic ^1.13 — DB migrations (`alembic.ini`, `src/migrations/`)
- TypeScript project references — `frontend/tsconfig.json` → `tsconfig.app.json` / `tsconfig.node.json`
- Oxlint ^1.71 — frontend lint (`npm run lint` in `frontend/package.json`)
- lucide-react — icons

## Key Dependencies

**Critical:**
- `fastapi` / `uvicorn` — API surface and process host
- `sqlalchemy[asyncio]` + `greenlet` — async ORM; greenlet required for async SQLAlchemy
- `aiosqlite` — local/dev/CI SQLite driver (`sqlite+aiosqlite://…`)
- `asyncpg` — PostgreSQL async driver (production-style URL in `.env.example`)
- `redis[hiredis]` — cache/session state; falls back to in-process `MockRedis` (`src/core/redis_client.py`)
- `numpy` — stochastic match simulation math (`src/shared/math_utils.py`, `src/modules/simulation/*`)
- `pydantic` / `pydantic-settings` / `python-dotenv` — settings from `.env`
- `react` / `react-dom` / `zustand` — SPA + shared game store
- `vite` / `typescript` / `tailwindcss` — frontend toolchain

**Infrastructure / declared but lightly used:**
- `alembic` — migrations; local SQLite often uses `Base.metadata.create_all` bootstrap in `src/main.py` instead of full migrate path
- `apscheduler` — listed in `pyproject.toml` but **not imported under `src/`** (unused dependency at map time)
- `psycopg2` — referenced only as sync URL scheme in `.env.example` for Alembic (`SYNC_DATABASE_URL`); not a Poetry dependency entry

## Configuration

**Environment:**
- Loaded via `pydantic_settings.BaseSettings` from `.env` (`src/core/config.py`)
- Template: `.env.example` (copy to `.env`; `.env` is gitignored)
- Required / primary vars:
  - `DATABASE_URL` — async SQLAlchemy URL
  - `SYNC_DATABASE_URL` — sync URL for Alembic
  - `REDIS_URL` — Redis URL or `mock` for in-memory
  - `SECRET_KEY` — present for future auth; **not used for JWT/session auth in application code**
  - `DEBUG`, `ENVIRONMENT`
- Game balance knobs also live on `Settings` (burnout, champion pool, coach comms, roster ages) in `src/core/config.py`

**Build:**
- Backend: `pyproject.toml`, `alembic.ini`
- Frontend: `frontend/package.json`, `frontend/vite.config.ts`, `frontend/tsconfig*.json`, `frontend/tailwind.config.js`, `frontend/postcss.config.js`, `frontend/vitest.config.ts`
- Docker infra only (DB/cache): `docker-compose.yml` (Postgres 16 + Redis 7) — no app container
- CI: `.github/workflows/ci.yml`
- Launcher: `run_game.bat` (pytest → frontend build → uvicorn → seed → vite)

## Platform Requirements

**Development:**
- Windows-friendly monorepo launcher (`run_game.bat`)
- Python 3.12 recommended; `venv/` at repo root
- Node.js 22+ with npm for `frontend/`
- Optional Docker Desktop for Postgres/Redis via `docker-compose.yml`
- Default local path: SQLite file DB + MockRedis (no Docker required)
- Ports: backend `8000`, frontend `5173`, Postgres `5432`, Redis `6379`

**Production:**
- Not containerized as a full app stack; target is local single-player management sim
- Intended data plane: PostgreSQL 16 (`postgres:16-alpine`) + Redis 7 (`redis:7-alpine`) when not on SQLite/MockRedis
- Frontend talks to hardcoded API base `http://127.0.0.1:8000` (`frontend/src/services/api.ts`)
- CORS open (`allow_origins=["*"]`) in `src/main.py` — suitable for local game, not multi-tenant prod

## Module Map (stack-relevant)

| Area | Path | Stack role |
|------|------|------------|
| API entry | `src/main.py` | FastAPI app, lifespan, CORS, SQLite bootstrap |
| Settings | `src/core/config.py` | Env + game rules |
| DB engine | `src/core/database.py` | Async engine/session |
| Cache | `src/core/redis_client.py` | Redis or MockRedis |
| HTTP routes | `src/api/routes/*.py` | REST surface |
| ORM models | `src/models/*.py` | SQLAlchemy models |
| Domain logic | `src/modules/{calendar,career,draft,simulation}/` | Pure game systems |
| Shared data/math | `src/shared/*` | CBLOL seed data, enums, numpy helpers |
| Frontend API client | `frontend/src/services/api.ts` | fetch → FastAPI |
| Frontend state | `frontend/src/store/useGameStore.ts` | Zustand |
| Career disk saves | `src/modules/career/save_service.py` | JSON under `saves/` |
| Seed CLI | `seed_runner.py` | HTTP seed against local API |
| Photo ingest | `scripts/fetch_player_photos.py` | Offline asset pipeline |

---

*Stack analysis: 2026-07-17*
