# Codebase Structure

**Analysis Date:** 2026-07-17

## Directory Layout

```
Moba Manager/
├── src/                          # Python backend package (FastAPI)
│   ├── main.py                   # App entry: lifespan, CORS, routers
│   ├── api/                      # HTTP boundary
│   │   ├── routes/               # One module per domain area
│   │   ├── schemas.py            # Pydantic request DTOs
│   │   ├── serializers.py        # Model → frontend JSON
│   │   └── calendar_helpers.py   # Week calendar response builder
│   ├── core/                     # Infrastructure (config, DB, Redis)
│   ├── models/                   # SQLAlchemy ORM entities
│   ├── modules/                  # Domain logic (no HTTP)
│   │   ├── calendar/             # Time SM, burnout, playoffs
│   │   ├── career/               # Save, finance, training, market…
│   │   ├── draft/                # Snake draft, AI, scout
│   │   └── simulation/           # Match engine + phase strategies
│   ├── shared/                   # Enums, seed data, math, exceptions
│   └── migrations/               # Alembic env + versions
├── frontend/                     # React + Vite SPA
│   ├── src/
│   │   ├── main.tsx              # React mount
│   │   ├── App.tsx               # Screen switcher
│   │   ├── screens/              # Full-page views
│   │   ├── components/           # Reusable UI widgets
│   │   ├── store/                # Zustand game store
│   │   ├── services/             # HTTP client (api.ts)
│   │   ├── lib/                  # Pure helpers + unit tests
│   │   ├── types/                # TS domain types
│   │   └── assets/               # Static images imported by UI
│   ├── public/                   # Static assets (players, art)
│   ├── package.json
│   ├── vite.config.ts
│   ├── vitest.config.ts
│   └── tailwind.config.js
├── tests/                        # Backend pytest suite
├── saves/                        # Career JSON slots (runtime)
├── scripts/                      # Ops utilities (e.g. photo fetch)
├── docs/                         # Design notes / handoff (Portuguese)
├── .planning/                    # GSD planning artifacts
├── alembic.ini
├── pyproject.toml                # Poetry deps + pytest config
├── docker-compose.yml            # Postgres 16 + Redis 7
├── seed_runner.py                # CLI seed helper
├── run_game.bat                  # Local launch helper
└── README.md
```

## Directory Purposes

**`src/`:**
- Purpose: Entire backend application package imported as `src.*`
- Contains: FastAPI app, API, domain modules, ORM, shared kernel
- Key files: `src/main.py`, `src/api/routes/__init__.py`

**`src/api/`:**
- Purpose: Thin HTTP layer only
- Contains: routers (`routes/*.py`), `schemas.py`, `serializers.py`, `calendar_helpers.py`
- Key files: `src/api/routes/teams.py` (largest surface: roster/finance/training/staff/org), `matches.py`, `draft.py`, `career.py`

**`src/core/`:**
- Purpose: Process infrastructure and DI primitives
- Contains: `config.py`, `database.py` (`get_db`, engine), `redis_client.py`
- Key files: `src/core/database.py`, `src/core/redis_client.py`

**`src/models/`:**
- Purpose: Durable schema
- Contains: `base.py` (Base + mixins), `player.py`, `team.py`, `contract.py`, `league.py`, `match.py`, `champion.py`, `patch.py`, `staff.py`
- Key files: `src/models/__init__.py` (exports all models for Alembic/metadata)

**`src/modules/calendar/`:**
- Purpose: In-game time progression and fatigue side effects
- Contains: `states.py`, `state_machine.py`, `calendar_service.py`, `burnout_service.py`, `fatigue_recovery.py`, `playoff_service.py`, `playoff_series.py`

**`src/modules/career/`:**
- Purpose: Manager progression systems outside pure match sim
- Contains: `*_service.py` modules — `save_service`, `finance_service`, `training_service`, `practice_service`, `morale_service`, `form_service`, `scouting_service`, `staff_service`, `org_service`, `academy_service`, `transfer_service`, `market_window`, `market_ai`, `free_agency`, `offseason_service`

**`src/modules/draft/`:**
- Purpose: Pre-match champion selection
- Contains: `snake_draft.py`, `draft_ai.py`, `draft_analyzer.py`, `draft_scout.py`, `scout_session.py`, `counter_matchup.py`
- Note: no `__init__.py` required for imports (namespace package style); import modules by path

**`src/modules/simulation/`:**
- Purpose: Match outcome engine and live playback
- Contains: `match_engine.py`, `match_engine_service.py`, `tactics.py`, `patch_service.py`, `match_depth.py`, `narration.py`, `coach_comms.py`, `champion_pool_validator.py`, `strategies/{base,early_game,mid_game,late_game}.py`

**`src/shared/`:**
- Purpose: Framework-agnostic shared code and static datasets
- Contains: enums, exceptions, CBLOL seed roster, champion catalog, global meta, round-robin and week calendar builders, math utils

**`src/migrations/`:**
- Purpose: Alembic migration scripts
- Contains: `env.py`, `versions/001_initial_schema.py`

**`frontend/src/screens/`:**
- Purpose: One file per hub or flow screen
- Contains: `MainMenu`, `NewGameWizard`, `Dashboard`, `Training`, `Staff`, `Organization`, `Squad`, `Standings`, `TransferMarket`, `PatchNotes`, `TacticsDraft`, `MatchSimulation`

**`frontend/src/components/`:**
- Purpose: Shared presentational pieces (shell, portraits, radar, map, grids)
- Key files: `GameShell.tsx`, `PlayerPortrait.tsx`, `SummonersRiftMap.tsx`, `PostMatchAnalysis.tsx`

**`frontend/src/store/`:**
- Purpose: Client application state
- Key files: `useGameStore.ts` (sole store)

**`frontend/src/services/`:**
- Purpose: Backend communication
- Key files: `api.ts`

**`frontend/src/lib/`:**
- Purpose: Pure functions + co-located vitest tests
- Contains: `hubAlerts.ts`, `orgBrands.ts`, `playerPhotoMap.ts`, `riftMap.ts`, `champions.ts` (+ `*.test.ts`)

**`frontend/src/types/`:**
- Purpose: Shared TS types/enums for UI
- Contains: `game.ts`, `screens.ts`

**`tests/`:**
- Purpose: Backend unit/integration tests (pytest + asyncio)
- Contains: `conftest.py` + `test_*.py` mirroring domain areas

**`saves/`:**
- Purpose: Runtime career JSON files written by `save_service`
- Generated: Yes (user play)
- Committed: optionally empty / user data — treat as data dir

**`docs/`:**
- Purpose: Human design docs, style bible, session handoffs (not runtime)

**`scripts/`:**
- Purpose: One-off tooling (e.g. `fetch_player_photos.py`)

## Key File Locations

**Entry Points:**
- `src/main.py`: FastAPI application object `app`
- `frontend/src/main.tsx`: SPA bootstrap
- `frontend/src/App.tsx`: top-level screen routing by store state
- `seed_runner.py`: optional seed CLI
- `run_game.bat`: Windows convenience launcher

**Configuration:**
- `src/core/config.py`: runtime settings (reads `.env` — do not commit secrets)
- `pyproject.toml`: Python deps, pytest asyncio mode
- `alembic.ini` + `src/migrations/`: migrations
- `docker-compose.yml`: Postgres + Redis services
- `frontend/vite.config.ts`, `tsconfig*.json`, `tailwind.config.js`, `postcss.config.js`
- `frontend/vitest.config.ts`: frontend unit tests

**Core Logic:**
- Calendar: `src/modules/calendar/calendar_service.py`, `state_machine.py`, `states.py`
- Match sim: `src/modules/simulation/match_engine.py`, `match_engine_service.py`
- Draft: `src/modules/draft/snake_draft.py`, `draft_ai.py`
- Career save: `src/modules/career/save_service.py`
- Seed data: `src/shared/cblol_2026_data.py`, `champions_data.py`
- Client orchestration: `frontend/src/store/useGameStore.ts`
- HTTP client: `frontend/src/services/api.ts`

**Testing:**
- Backend: `tests/test_*.py`, fixtures in `tests/conftest.py`
- Frontend pure helpers: `frontend/src/lib/*.test.ts`

## Naming Conventions

**Files (backend):**
- Domain services: `*_service.py` (e.g. `finance_service.py`, `calendar_service.py`)
- Route modules: short plural/domain noun (`teams.py`, `matches.py`, `draft.py`)
- Models: singular entity name (`player.py`, `team.py`)
- Pure engines: descriptive noun (`snake_draft.py`, `match_engine.py`, `state_machine.py`)

**Files (frontend):**
- Screens: PascalCase component file matching export (`Dashboard.tsx`, `TacticsDraft.tsx`)
- Components: PascalCase (`GameShell.tsx`, `AttributeRadar.tsx`)
- Store hooks: `use*.ts` (`useGameStore.ts`)
- Lib helpers: camelCase (`hubAlerts.ts`, `orgBrands.ts`)
- Tests: `*.test.ts` co-located with helper under `lib/`

**Directories:**
- Python packages: lowercase (`modules/career/`, `api/routes/`)
- Frontend feature folders: lowercase plural/role (`screens/`, `components/`, `services/`)

**Symbols:**
- Python classes: PascalCase (`CalendarService`, `MatchEngine`, `SnakeDraft`)
- Python functions: snake_case (`advance_all_leagues`, `serialize_player`)
- Python enums: PascalCase type, UPPER_SNAKE members (`SplitPhase.REGULAR_SEASON`)
- TS components: PascalCase; store actions camelCase
- JSON API player fields: camelCase (`currentAbility`, `burnoutMeter`) despite Python snake_case

## Where to Add New Code

**New REST endpoint:**
- Primary: new handler in the matching file under `src/api/routes/` (or new module + register in `src/api/routes/__init__.py` `include_routers`)
- Request DTO: `src/api/schemas.py`
- Response shaping: `src/api/serializers.py` or inline dict if one-off
- Business logic: **not** in the route — add/extend service under `src/modules/{domain}/`

**New career/manager system (training-like):**
- Implementation: `src/modules/career/<name>_service.py`
- Routes: usually under `src/api/routes/teams.py` as `/teams/{team_id}/...` or dedicated router if large
- Redis keys: namespace as `<domain>:*` and include patterns in `save_service.CAREER_REDIS_PATTERNS` / `redis_client.flush_game_state` if session-scoped
- Tests: `tests/test_<name>.py`
- Frontend: API method in `frontend/src/services/api.ts`, state slice + actions in `useGameStore.ts`, screen under `frontend/src/screens/` if full page

**New match/simulation rule:**
- Phase math: `src/modules/simulation/strategies/` or helpers in `match_depth.py` / `tactics.py`
- Orchestration: `match_engine.py` (batch) or `match_engine_service.py` (live)
- Config knobs: `src/core/config.py` Settings fields
- Tests: `tests/test_match_engine.py`, `test_match_depth.py`, etc.

**New draft behavior:**
- Order/rules: `src/modules/draft/snake_draft.py`
- AI scoring: `draft_ai.py` / `counter_matchup.py` / `draft_analyzer.py`
- Scout UX: `draft_scout.py` + routes in `src/api/routes/draft.py`
- Frontend: `frontend/src/screens/TacticsDraft.tsx` + store draft fields

**New calendar phase or day type:**
- State classes: `src/modules/calendar/states.py`
- Orchestration: `state_machine.py` / `calendar_service.py`
- Enums: `src/shared/enums.py` (`SplitPhase`, `CalendarDayType`)
- Week UI grid: `src/shared/week_calendar.py` + `src/api/calendar_helpers.py`

**New ORM entity:**
- Model file: `src/models/<entity>.py` inheriting `Base, UUIDMixin, TimestampMixin` from `src/models/base.py`
- Export in `src/models/__init__.py`
- Alembic revision under `src/migrations/versions/`
- Do **not** use `src.core.database.Base` for new models

**New frontend screen:**
- Component: `frontend/src/screens/MyScreen.tsx`
- Add id to `frontend/src/types/screens.ts` (`AppScreen`)
- Wire switch in `frontend/src/App.tsx`
- Add nav entry in `frontend/src/components/GameShell.tsx` `NAV` array
- Extend `currentScreen` union / actions in `useGameStore.ts`

**New pure UI helper:**
- `frontend/src/lib/<name>.ts` + `frontend/src/lib/<name>.test.ts`

**New backend unit test:**
- `tests/test_<area>.py` using fixtures from `tests/conftest.py`
- Prefer testing `src/modules/*` directly; use API integration tests sparingly (`test_api_integration.py`)

**Shared constants / seed content:**
- Static CBLOL rosters/meta: `src/shared/cblol_2026_data.py`, `global_meta_data.py`, `champions_data.py`
- Cross-cutting enums/errors: `src/shared/enums.py`, `exceptions.py`

## Special Directories

**`venv/`:**
- Purpose: Local Python virtualenv
- Generated: Yes
- Committed: No — exclude from exploration and commits

**`frontend/node_modules/`:**
- Purpose: npm packages
- Generated: Yes
- Committed: No

**`frontend/dist/`:**
- Purpose: Vite production build output
- Generated: Yes
- Committed: May exist in tree; treat as build artifact

**`saves/`:**
- Purpose: Career slot JSON (`{slot}.json`)
- Generated: Yes (playtime)
- Committed: Data only; schema owned by `save_service.SAVE_VERSION`

**`.planning/`:**
- Purpose: GSD maps/plans (this document lives in `.planning/codebase/`)
- Generated: Partially (tooling)
- Committed: Yes (project process)

**`lol_manager.db`:**
- Purpose: Local SQLite database file when configured
- Generated: Yes
- Committed: Environment-specific

**`docs/`:**
- Purpose: Long-form product/design notes (Portuguese)
- Generated: No
- Committed: Yes

---

*Structure analysis: 2026-07-17*
