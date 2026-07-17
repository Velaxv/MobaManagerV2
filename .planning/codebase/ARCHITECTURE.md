<!-- refreshed: 2026-07-17 -->
# Architecture

**Analysis Date:** 2026-07-17

## System Overview

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                     Frontend (React 19 + Vite + Zustand)                    │
│  screens/*  ·  components/*  ·  store/useGameStore.ts  ·  services/api.ts   │
└────────────────────────────────────┬────────────────────────────────────────┘
                                     │ HTTP JSON (127.0.0.1:8000)
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        API Layer (FastAPI routers)                          │
│              `src/main.py` → `src/api/routes/*` (include_routers)           │
│              schemas: `src/api/schemas.py`  serializers: `serializers.py`   │
└──────────┬──────────────────────────┬──────────────────────────┬────────────┘
           │                          │                          │
           ▼                          ▼                          ▼
┌────────────────────┐  ┌────────────────────┐  ┌────────────────────────────┐
│  calendar module   │  │  career module     │  │  draft + simulation        │
│  State Machine     │  │  save/finance/     │  │  SnakeDraft · DraftAI      │
│  Burnout · Playoff │  │  training/market…  │  │  MatchEngine (Strategy)    │
│ `src/modules/      │  │ `src/modules/      │  │ `src/modules/draft/`       │
│  calendar/`        │  │  career/`          │  │ `src/modules/simulation/`  │
└─────────┬──────────┘  └─────────┬──────────┘  └─────────────┬──────────────┘
          │                       │                           │
          ▼                       ▼                           ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Shared + Persistence                                 │
│  Models `src/models/*`  ·  Enums/data `src/shared/*`                         │
│  SQLAlchemy async (`src/core/database.py`)  ·  Redis (`src/core/redis_client`)│
│  Career JSON saves (`saves/*.json`)  ·  Alembic (`src/migrations/`)          │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| FastAPI app | Lifespan, CORS, router mount | `src/main.py` |
| Router registry | Include all API routers | `src/api/routes/__init__.py` |
| HTTP routes | Request validation, DI, HTTP mapping | `src/api/routes/*.py` |
| Pydantic DTOs | Request body shapes | `src/api/schemas.py` |
| Serializers | Domain → JSON for frontend | `src/api/serializers.py` |
| Calendar helpers | Week calendar payload for hub | `src/api/calendar_helpers.py` |
| Settings | Env-backed game/config knobs | `src/core/config.py` |
| DB engine/session | Async SQLAlchemy + `get_db` | `src/core/database.py` |
| Redis client | Ephemeral game state + MockRedis fallback | `src/core/redis_client.py` |
| ORM models | Persistent entities | `src/models/*.py` |
| Calendar SM | Day advance, phase transitions | `src/modules/calendar/` |
| Career services | Save, finance, training, market, org… | `src/modules/career/` |
| Draft engine | Official 20-action snake draft + AI | `src/modules/draft/` |
| Match engine | Stochastic Early/Mid/Late simulation | `src/modules/simulation/` |
| Shared domain | Enums, seed data, math, exceptions | `src/shared/` |
| Zustand store | Client game state + API orchestration | `frontend/src/store/useGameStore.ts` |
| API client | Typed fetch wrappers | `frontend/src/services/api.ts` |
| Screens | Full-page UI modes | `frontend/src/screens/*.tsx` |
| Game shell | Hub chrome / nav | `frontend/src/components/GameShell.tsx` |

## Pattern Overview

**Overall:** Layered modular monolith (SPA + REST API) with domain modules behind thin FastAPI routers.

**Key Characteristics:**
- **Backend domain packages** under `src/modules/{calendar,career,draft,simulation}/` own business rules; routes orchestrate and serialize.
- **Dual runtime state:** durable data in SQL (players, teams, matches, leagues); session/ephemeral state in Redis (calendar SM, live match, draft, scouting, training, patch cache).
- **Career continuity:** JSON slot saves under `saves/` snapshot DB-relevant fields + Redis blob (`src/modules/career/save_service.py`).
- **Frontend is screen-driven:** no React Router; `App.tsx` switches on Zustand `gameState` / `currentScreen`.
- **Design patterns in engines:** State Pattern (calendar), Strategy Pattern (match phases), pure domain classes for draft (SnakeDraft / DraftAI).

## Layers

**Presentation (Frontend):**
- Purpose: Manager UI, hub navigation, interactive draft and live match visualization
- Location: `frontend/src/`
- Contains: screens, components, Zustand store, API client, pure UI helpers (`lib/`)
- Depends on: Backend HTTP API only (`frontend/src/services/api.ts` → `http://127.0.0.1:8000`)
- Used by: Browser

**API (HTTP boundary):**
- Purpose: REST endpoints, request validation, dependency injection of `AsyncSession`
- Location: `src/api/`
- Contains: route modules, Pydantic schemas, player/team serializers, calendar response helpers
- Depends on: `src/modules/*`, `src/models/*`, `src/core/*`
- Used by: Frontend

**Domain modules:**
- Purpose: Game rules and simulation
- Location: `src/modules/`
- Contains:
  - `calendar/` — State Machine, burnout, playoffs
  - `career/` — save/load, finance, training, practice, morale, form, market, staff, academy, org, scouting, offseason, free agency
  - `draft/` — SnakeDraft, DraftAI, analyzer, scout advisor/session, counter matchup
  - `simulation/` — MatchEngine, live MatchEngineService, phase strategies, tactics, patch meta, narration, coach comms
- Depends on: `src/models`, `src/shared`, `src/core`
- Used by: API routes (and occasionally other modules)

**Shared kernel:**
- Purpose: Cross-cutting enums, exceptions, seed datasets, math helpers, schedule builders
- Location: `src/shared/`
- Contains: `enums.py`, `exceptions.py`, `math_utils.py`, `cblol_2026_data.py`, `champions_data.py`, `global_meta_data.py`, `round_robin.py`, `week_calendar.py`
- Depends on: stdlib / minimal
- Used by: models, modules, API

**Persistence / infrastructure:**
- Purpose: DB sessions, Redis, config, migrations
- Location: `src/core/`, `src/models/`, `src/migrations/`, `saves/`
- Contains: async engine, Redis client (real or `MockRedis`), ORM tables, Alembic env
- Depends on: settings from `.env` via `src/core/config.py`
- Used by: all backend layers

## Data Flow

### Primary Request Path (hub day advance)

1. User advances day on Dashboard → Zustand action calls API (`frontend/src/store/useGameStore.ts`, `frontend/src/services/api.ts`)
2. `POST /calendar/advance` (`src/api/routes/calendar.py`) injects `AsyncSession` via `get_db`
3. `CalendarService.advance_all_leagues` (`src/modules/calendar/calendar_service.py`) loads/creates `CalendarStateMachine` per league
4. SM advances one day, persists context to Redis key `calendar:league:{id}:state` (`src/modules/calendar/state_machine.py`, `src/core/redis_client.py`)
5. On match days, non-managed fixtures auto-simulate via draft + `MatchEngine`; managed team match is left for the player
6. Burnout / fatigue applied (`src/modules/calendar/burnout_service.py`, `fatigue_recovery.py`)
7. League row synced in SQL; response returns results + week calendar for UI refresh

### Match simulation path (batch)

1. `POST /matches/simulate` (`src/api/routes/matches.py`)
2. Load teams from SQL → run full `SnakeDraft` with `DraftAI` auto-fills
3. `calculate_draft_penalties` + patch meta from Redis (`patch:current:meta`)
4. `MatchEngine.simulate(MatchInput)` runs Early → Mid → Late strategies (`src/modules/simulation/match_engine.py`, `strategies/*`)
5. Persist `Match` + standings updates; optional Redis result cache

### Live match path

1. `POST /matches/live/start` creates live session
2. Module singleton `MatchEngineService` (`src/modules/simulation/match_engine_service.py`, mounted in `matches.py`) advances phases over time, stores `LiveMatchState` in Redis (`live_match:*`)
3. Frontend polls `GET /matches/live/{match_id}/state`; coach comms via `POST .../coach-comm`
4. Events include map metadata for `SummonersRiftMap` UI component

### Interactive draft path

1. Frontend holds draft turn state in Zustand; on AI turns calls `POST /draft/ai-decision`
2. Backend rebuilds `DraftState` from request body (`src/api/routes/draft.py`) and runs `DraftAI`
3. Scout advice/session endpoints (`/draft/scout-*`) score recommendations and track follow-through

### Career new / save / load

1. `POST /career/new` flushes Redis game keys, force-reseeds CBLOL data, returns managed team by abbreviation (`src/api/routes/career.py`)
2. `POST /career/save` writes slot JSON via `save_service` (DB entities + Redis snapshot)
3. `POST /career/load/{slot}` restores SQL fields + Redis import; UUIDs must match seed universe

**State Management:**
- **Server durable:** PostgreSQL or SQLite via SQLAlchemy async (`src/core/database.py`)
- **Server ephemeral:** Redis keys namespaced by domain (`career:*`, `calendar:*`, `draft:*`, `live_match:*`, …); auto-fallback to in-memory `MockRedis`
- **Client:** Single Zustand store `useGameStore` holds screen, calendar, roster, market, live match logs, org/training/scouting snapshots
- **Career files:** `saves/{slot}.json` (versioned `SAVE_VERSION = 2`)

## Key Abstractions

**Calendar State Machine:**
- Purpose: Split phases OFFSEASON → PRESEASON → REGULAR_SEASON → PLAYOFFS with day types (REST/TRAINING/MATCH_DAY/…)
- Examples: `src/modules/calendar/states.py`, `src/modules/calendar/state_machine.py`
- Pattern: GoF State — `CalendarState` subclasses + serializable `CalendarContext`

**MatchEngine + Phase Strategy:**
- Purpose: Stochastic full-match simulation from draft inputs
- Examples: `src/modules/simulation/match_engine.py`, `strategies/base.py`, `early_game.py`, `mid_game.py`, `late_game.py`
- Pattern: Strategy — each phase returns `PhaseResult` / `TeamMatchState`; engine aggregates winner and logs

**SnakeDraft / DraftAI:**
- Purpose: Official 20-action competitive draft order; AI picks/bans; penalty scoring for off-pool comps
- Examples: `src/modules/draft/snake_draft.py`, `draft_ai.py`, `draft_analyzer.py`, `draft_scout.py`
- Pattern: Pure domain state machine + decision agent; Redis optional for session/scout history

**Career services (`*_service.py`):**
- Purpose: One service class per career subsystem (finance, training, staff, org, market window, …)
- Examples: `src/modules/career/finance_service.py`, `training_service.py`, `transfer_service.py`, `save_service.py`
- Pattern: Service layer instantiated with `AsyncSession` (and Redis as needed)

**ORM models with mixins:**
- Purpose: UUID PKs + timestamps + domain constraints
- Examples: `src/models/base.py` (`UUIDMixin`, `TimestampMixin`), `player.py`, `team.py`, `match.py`, `league.py`
- Pattern: SQLAlchemy 2.0 mapped columns; business helpers on models (e.g. `Team.validate_roster_size`)

**Shared enums & exceptions:**
- Purpose: Single source for roles, phases, draft actions; typed error codes
- Examples: `src/shared/enums.py`, `src/shared/exceptions.py`
- Pattern: `str, Enum` for JSON friendliness; `LolManagerException` hierarchy with `code`

**Frontend screen machine:**
- Purpose: Menu → New Game → Playing hub screens without a router package
- Examples: `frontend/src/App.tsx`, `frontend/src/types/screens.ts`, `GameShell.tsx`
- Pattern: Explicit switch on store fields; hub nav groups (routine / squad / club / compete)

## Entry Points

**Backend API:**
- Location: `src/main.py`
- Triggers: `uvicorn src.main:app` (or project batch `run_game.bat`)
- Responsibilities: lifespan (Redis connect, SQLite bootstrap), CORS, `include_routers(app)`

**Router aggregation:**
- Location: `src/api/routes/__init__.py` → `include_routers`
- Triggers: app startup
- Responsibilities: mount health, seed, calendar, teams, leagues, market, champions, matches, draft, offseason, career, patches

**Frontend SPA:**
- Location: `frontend/src/main.tsx` → `App.tsx`
- Triggers: Vite dev server / static build
- Responsibilities: mount React root; initial `loadData()` from store

**DB seed:**
- Location: `src/api/routes/seed.py`, helper `seed_runner.py`, data `src/shared/cblol_2026_data.py`
- Triggers: `POST /db/seed`, new career flow
- Responsibilities: populate CBLOL 2026 teams/players/champions/league schedule

**Migrations:**
- Location: `src/migrations/env.py`, `versions/001_initial_schema.py`, `alembic.ini`
- Triggers: Alembic CLI (sync URL from settings)
- Responsibilities: schema evolution (local SQLite also auto-creates + light ALTER in lifespan)

## Architectural Constraints

- **Threading:** Async event loop (FastAPI/uvicorn). SQLAlchemy async sessions; live match service uses asyncio tasks. SQLite uses `check_same_thread=False` and PRAGMA foreign_keys.
- **Global state:**
  - `redis_client` singleton (`src/core/redis_client.py`)
  - `get_settings()` LRU-cached (`src/core/config.py`)
  - `match_engine_service = MatchEngineService()` module singleton in `src/api/routes/matches.py`
  - Zustand single store on client
- **Circular imports:** Domain modules sometimes import inside functions (routes, patch cache) to avoid import cycles — prefer that pattern for route→module optional deps.
- **Dual Base classes:** `src/models/base.py` defines the declarative `Base` used by models; `src/core/database.py` also defines a `DeclarativeBase` named `Base` but app import path uses `from src.models import Base` in `main.py`. New models must inherit `src.models.base.Base` (via mixins package), not the database module Base.
- **Identity stability:** Career load assumes seed UUIDs stable (`SEED_TAG = cblol_2026_v1`). Force reseed invalidates old saves.
- **No auth layer:** Local single-player manager; CORS open (`allow_origins=["*"]`). Do not introduce multi-user assumptions without an auth design.
- **API base URL hardcoded** in `frontend/src/services/api.ts` (`http://127.0.0.1:8000`) — local-dev architecture.

## Anti-Patterns

### Fat route orchestration

**What happens:** `src/api/routes/matches.py` embeds full draft loop + engine wiring inline instead of a single application service method.
**Why it's wrong:** Harder to reuse (batch vs live vs calendar auto-sim) and to unit-test without HTTP.
**Do this instead:** Keep HTTP thin; put orchestration in `MatchEngineService` / a dedicated `simulate_match_for_teams(...)` in `src/modules/simulation/` (live path already partially does this).

### Business rules only on the client

**What happens:** Draft turn UI state lives in Zustand while AI decisions hit the backend.
**Why it's wrong:** Divergent validation if FE order drifts from `DRAFT_ORDER`.
**Do this instead:** Treat backend `SnakeDraft` / `DRAFT_ORDER` as source of truth; FE should mirror enums from shared types (`frontend/src/types/game.ts`) and re-validate critical actions server-side when persisting.

### Redis as sole source without SQL mirror where needed

**What happens:** Calendar SM lives primarily in Redis; league table is synced by service.
**Why it's wrong:** Redis flush or MockRedis process restart can desync week/day from `League` row if sync path is skipped.
**Do this instead:** Always advance through `CalendarService` (which syncs SQL); never mutate Redis calendar keys ad-hoc from routes.

### Dual declarative Base

**What happens:** Two `Base` definitions (`src/models/base.py` vs `src/core/database.py`).
**Why it's wrong:** Metadata/create_all only sees models registered on the imported Base.
**Do this instead:** Inherit models from `src.models.base.Base` only; treat `database.Base` as legacy/unused for new code.

## Error Handling

**Strategy:** Domain raises `LolManagerException` subclasses with `code`; routes catch domain/validation failures and map to `HTTPException` (400/404/500). `get_db` commits on success, rolls back on exception.

**Patterns:**
- Domain: `src/shared/exceptions.py` (`InvalidDraftAction`, `InsufficientBudget`, `CalendarStateError`, …)
- HTTP: `HTTPException(status_code=..., detail=...)` in route try/except blocks
- Logging: module loggers (`logging.getLogger(__name__)` or `"lol_manager_api"`); lifespan logs connection lifecycle
- Client: `api.ts` fetch wrappers surface errors to store actions (user-visible toasts/messages on screens)

## Cross-Cutting Concerns

**Logging:** stdlib logging, INFO default in `src/main.py`; domain modules log SM transitions, draft decisions, sim outcomes.

**Validation:**
- Pydantic request models in `src/api/schemas.py`
- SQLAlchemy CheckConstraints on player attributes / team budget
- Model methods (`Team.validate_roster_size`, age rules via settings + exceptions)
- Draft action validation inside `SnakeDraft.process_action`

**Authentication:** Not applicable — single-player local manager; no JWT/session auth middleware.

**Configuration:** `pydantic-settings` `Settings` in `src/core/config.py` (`.env`): DB URLs, Redis URL, burnout/champion-pool/coach-comms tuning knobs.

**CORS:** Wide-open for local SPA ↔ API development (`src/main.py`).

**Serialization naming:** API JSON uses camelCase field names for players (`currentAbility`, `teamId`) via `src/api/serializers.py`; Python domain stays snake_case.

---

*Architecture analysis: 2026-07-17*
