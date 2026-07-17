<!-- refreshed: 2026-07-17 -->
---
last_mapped_commit: 65e8aea3129b111ef8f8a20fcb3b4d218c70cbde
---
# External Integrations

**Analysis Date:** 2026-07-17

## APIs & External Services

**Riot Games Data Dragon (CDN — read-only, runtime UI):**
- Service: Champion portraits, splash, and loading images
- Client: URL builders in `frontend/src/lib/champions.ts`
- Usage: `ChampionImage` (`frontend/src/components/ChampionImage.tsx`) loads remote PNGs/JPGs
- Version pin: Data Dragon `15.8.1`
- Base: `https://ddragon.leagueoflegends.com/cdn/15.8.1/...`
- Auth: None (public CDN)
- Offline impact: Missing images fall back to empty/failed UI state when CDN unreachable

**Leaguepedia / lol.fandom MediaWiki API (offline asset pipeline only):**
- Service: Player portrait discovery and download for CBLOL nicks
- Client: stdlib `urllib` in `scripts/fetch_player_photos.py`
- Endpoint: `https://lol.fandom.com/api.php`
- Outputs: `frontend/public/players/*.jpg`, `frontend/public/players/_meta.json`, regenerates `frontend/src/lib/playerPhotoMap.ts`
- Auth: None (User-Agent `MobaManagerPhotoBot/1.0`)
- Runtime game path does **not** call fandom; only static files under `frontend/public/players/`

**Google Fonts (runtime UI):**
- Service: Inter + JetBrains Mono webfonts
- Wired in `frontend/index.html` via `fonts.googleapis.com` / `fonts.gstatic.com`
- Auth: None

**Internal FastAPI (frontend ↔ backend, local loopback):**
- Base URL hardcoded: `http://127.0.0.1:8000` in `frontend/src/services/api.ts`
- Client: browser `fetch` wrapper exported as `api` object
- Seed tooling also hits the same host (`seed_runner.py`)
- OpenAPI/Swagger available at `/docs` when server is up

## Data Storage

**Databases:**
- **SQLite (default local/CI)**
  - Connection: `DATABASE_URL` (e.g. `sqlite+aiosqlite:///./…`)
  - Client: SQLAlchemy async + `aiosqlite` (`src/core/database.py`)
  - File example: `lol_manager.db` at repo root (gitignored)
  - Bootstrap: on startup, if SQLite URL, `Base.metadata.create_all` + light PRAGMA column migrate (`src/main.py`)
- **PostgreSQL 16 (docker-compose / production-style)**
  - Image: `postgres:16-alpine` in `docker-compose.yml` (`lol_manager_postgres`)
  - DB/user defaults in compose: `lol_manager_db` / `lol_admin` (password only in local compose/env template)
  - Connection: `DATABASE_URL=postgresql+asyncpg://…` (`.env.example`)
  - Sync migrations: `SYNC_DATABASE_URL=postgresql+psycopg2://…` consumed by Alembic (`src/migrations/env.py`, `alembic.ini`)
  - Volume: named `postgres_data`

**Cache / ephemeral session state:**
- **Redis 7** (`redis:7-alpine` in `docker-compose.yml`)
  - Connection: `REDIS_URL` (default `redis://localhost:6379`)
  - Client: `redis.asyncio` with hiredis when available (`src/core/redis_client.py`)
  - Config: no AOF, `maxmemory 256mb`, `allkeys-lru`
- **MockRedis** in-process dict store when `REDIS_URL=mock`, non-localhost URL mode, or connect failure
  - Used heavily for calendar, draft, playoffs, match results, burnout counters, career session keys
  - CI sets `REDIS_URL=mock`

**File Storage:**
- Career save/load JSON slots under `saves/{slot}.json` (`src/modules/career/save_service.py`) — gitignored
- Static frontend assets: `frontend/public/art/`, `frontend/public/players/`
- No cloud object storage (S3/GCS/etc.)

**ORM / migrations:**
- Models: `src/models/*.py` (player, team, contract, league, match, champion, patch, staff, …)
- Alembic script location: `src/migrations/` (initial revision `src/migrations/versions/001_initial_schema.py`)

## Authentication & Identity

**Auth Provider:**
- None implemented for end users
- Single-player local game; API is open on localhost
- `SECRET_KEY` exists in Settings / `.env.example` for potential JWT signing — **no JWT, OAuth, session cookies, or Authorization middleware in route code**
- CORS: fully open (`allow_origins=["*"]`) in `src/main.py`

## Monitoring & Observability

**Error Tracking:**
- None (no Sentry/Datadog/etc.)

**Logs:**
- Python `logging` basicConfig in `src/main.py` (`INFO`, timestamped format, logger name `lol_manager_api`)
- Module loggers (e.g. Redis client, save service)
- Alembic logging via `alembic.ini` (console WARN/INFO)

**Health:**
- `GET /` health/root payload in `src/api/routes/health.py` (`status`, `engine_version`, `environment`)

## CI/CD & Deployment

**Hosting:**
- Local desktop/dev only; no cloud deploy config
- Remote repo noted in docs: GitHub `Velaxv/MobaManagerV2`

**CI Pipeline:**
- GitHub Actions: `.github/workflows/ci.yml`
  - Triggers: push/PR to `main` or `master`
  - Job `backend`: Python 3.12, pip-install deps from workflow list, `pytest tests` with SQLite + `REDIS_URL=mock`
  - Job `frontend`: Node 22, `npm ci`, `npm run build` in `frontend/`

**Local orchestration:**
- `run_game.bat` — sequential: backend pytest → frontend production build check → start Uvicorn → seed → Vite dev → open browser
- `docker-compose.yml` — Postgres + Redis only (not the app)

## Environment Configuration

**Required env vars (see `.env.example`):**
- `DATABASE_URL` — async DB URL for FastAPI/SQLAlchemy
- `SYNC_DATABASE_URL` — sync DB URL for Alembic
- `REDIS_URL` — Redis URL or `mock`
- `SECRET_KEY` — reserved secret (unused by auth today)
- `DEBUG` — SQL echo / debug mode
- `ENVIRONMENT` — `development` | `staging` | `production`

**Optional / operational:**
- `SEED_FORCE=1` — force destructive reseed via `seed_runner.py`
- Game balance settings optional overrides on same Settings object (`min_age_erl`, burnout thresholds, etc. in `src/core/config.py`)

**Secrets location:**
- Local `.env` (gitignored); template `.env.example` committed
- Docker Compose embeds local Postgres password for dev only — do not reuse for real deployments
- Never commit `.env`, `*.db`, or `saves/`

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None (no webhook dispatchers)

## Integration Touchpoints by Layer

| Integration | Direction | When | Code |
|-------------|-----------|------|------|
| Frontend → FastAPI | Outbound HTTP | Runtime gameplay | `frontend/src/services/api.ts`, `frontend/src/store/useGameStore.ts` |
| seed_runner → FastAPI | Outbound HTTP | Launch/seed | `seed_runner.py` → `/db/seed`, `/db/seed/status` |
| UI → Data Dragon CDN | Outbound image GET | Champion art | `frontend/src/lib/champions.ts` |
| Script → lol.fandom API | Outbound HTTP | Manual asset refresh | `scripts/fetch_player_photos.py` |
| Browser → Google Fonts | Outbound CSS/font | Page load | `frontend/index.html` |
| App → SQLite/Postgres | DB | Always | `src/core/database.py` |
| App → Redis/MockRedis | Cache | Session state | `src/core/redis_client.py` |
| App → `saves/*.json` | Disk | Career save/load | `src/modules/career/save_service.py` |

## API Surface (internal routers)

Registered in `src/api/routes/__init__.py`:
- `health` — root/status
- `seed` — DB seed / status
- `calendar` — week advance, calendar state
- `teams` — roster, finance, training, practice, scouting, academy
- `leagues` — standings, matches, playoffs
- `market` — free agents / transfers
- `champions` — champion catalog
- `matches` — live match sim, coach comms, speed
- `draft` — snake draft / AI / scout
- `offseason` — renew/release/new split
- `career` — new career, save/load slots
- `patches` — patch notes / badges

## Dependency Risks for Integrations

- Hardcoded `API_BASE` prevents easy remote hosting without frontend change (`frontend/src/services/api.ts`)
- Data Dragon version pin can drift from live LoL patches until manually updated
- Leaguepedia scraping is best-effort offline tooling (rate limits / page renames)
- Redis optional by design; MockRedis does not implement full Redis semantics (TTL ignored, pub/sub is log-only)
- `apscheduler` declared but unused — no scheduled external sync jobs

---

*Integration audit: 2026-07-17*
