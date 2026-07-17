# Codebase Concerns

**Analysis Date:** 2026-07-17

## Tech Debt

**MockRedis as default session store (state lost on restart):**
- Issue: Dev mode uses in-memory `MockRedis` (`src/core/redis_client.py`). Career session state (calendar SM, playoffs, moral, org, form, training, scouting, practice, live match, draft, patch cache, burnout counters) lives in Redis keys. Restarting uvicorn clears the process store even when SQLite/`lol_manager.db` remains.
- Files: `src/core/redis_client.py`, `src/main.py` (lifespan connect/disconnect), consumers across `src/modules/career/*`, `src/modules/calendar/*`, `src/modules/simulation/match_engine_service.py`
- Impact: Mid-career restart loses week/day SM, playoff bracket, board/morale, live mid-match; playtest “continue after reboot” only works after explicit save/load or reseed. `MockRedis.setex` **ignores TTL** (keys never expire).
- Fix approach: Prefer real Redis when available (`docker-compose.yml` already defines Redis 7); keep Mock only for tests/offline. Document `REDIS_URL` for local real Redis. Optionally persist hot keys on graceful shutdown. Fix connect heuristic (see Known Bugs).

**Save/load incomplete for mid-match / draft:**
- Issue: `CareerSaveService` (save_version 2) snapshots DB rows + calendar/playoffs + career Redis patterns (`career:*`, `training:*`, `scouting:*`, `practice:*`, `patch:current:*`, `market:ai:*`) but **does not** export `live_match:*` or `draft:*`.
- Files: `src/modules/career/save_service.py` (`CAREER_REDIS_PATTERNS`, `_export_career_redis`), `src/core/redis_client.py` (`export_snapshot` / `import_snapshot`)
- Impact: Save during draft or live match cannot resume that match after load/restart. User must finish map before save or abandon in-progress live state.
- Fix approach: Optional IN-1 extension — snapshot active `live_match:{id}` + draft keys, or block save while live/draft is open and surface UI warning.

**Seed still destructive when forced; new career defaults to reseed:**
- Issue: IN-4 made default seed safe (`force=false` skips if seeded — `src/api/routes/seed.py`, `seed_runner.py`). But `POST /db/seed?force=true` still runs `Base.metadata.drop_all` + new UUIDs. `NewCareerRequest.force_reseed` defaults to **`True`** (`src/api/schemas.py`); FE always sends `force_reseed: true` (`frontend/src/store/useGameStore.ts`).
- Files: `src/api/routes/seed.py`, `src/api/routes/career.py`, `src/api/schemas.py`, `frontend/src/store/useGameStore.ts`, `frontend/src/services/api.ts`
- Impact: “Nova carreira” wipes DB and invalidates existing save slots (UUID mismatch). Accidental force seed from API/docs still destroys progress.
- Fix approach: Keep force gated; require explicit UI confirm; never expose force on unauthenticated network; document that saves need matching seed UUIDs (`SEED_TAG` / load mismatch warning in `save_service.py`).

**God modules / oversized UI state:**
- Issue: Several files concentrate too many responsibilities, making changes high-risk.
- Files (approx lines):
  - `frontend/src/store/useGameStore.ts` (~1770) — all screens’ state + API orchestration
  - `src/modules/simulation/match_engine_service.py` (~1600) — live loop, map state, post-match side effects
  - `frontend/src/screens/TacticsDraft.tsx` (~1186)
  - `src/modules/calendar/calendar_service.py` (~855) — day advance + training/scout/practice/finance/org/market/auto-sim
  - `frontend/src/services/api.ts` (~900)
  - `src/modules/draft/draft_scout.py` (~944)
- Impact: Hard to test in isolation; regressions when touching one career system; review fatigue.
- Fix approach: Split post-match pipeline out of live loop; slice Zustand by domain (career / competition / live); extract calendar day-processors into a pipeline registry.

**Dual match engines (batch vs live):**
- Issue: Auto-sim / `POST /matches/simulate` uses `MatchEngine` + Early/Mid/Late strategies (`src/modules/simulation/match_engine.py`, `strategies/*`). Interactive live uses a separate tick loop in `MatchEngineService` with different formulas, map structures, win reasons, ratings.
- Files: `src/modules/simulation/match_engine.py`, `src/modules/simulation/match_engine_service.py`, `src/api/routes/matches.py`, `src/modules/calendar/calendar_service.py` (`_auto_simulate_match`)
- Impact: Balance and “why we won” differ for manager games vs auto-simmed opponents; tests of batch engine do not guarantee live behavior.
- Fix approach: Share core tick/resolution helpers; drive both paths from one pure simulator + thin live scheduler.

**SQLite bootstrap vs Alembic:**
- Issue: Local SQLite uses `create_all` + ad-hoc `PRAGMA`/`ALTER` for `players.is_starter` in `src/main.py` `_sqlite_bootstrap`. Alembic has only `src/migrations/versions/001_initial_schema.py`. New columns risk silent missing schema if only create_all runs on existing DB.
- Files: `src/main.py`, `src/migrations/env.py`, `src/migrations/versions/001_initial_schema.py`, `src/core/database.py`
- Impact: Dev DBs diverge; production Postgres path may not match local SQLite.
- Fix approach: Prefer Alembic for all schema changes; remove one-off light migrates or generate them as real revisions.

**Silent failure absorption in calendar/match pipelines:**
- Issue: Many `except Exception` blocks log and continue (training, scouting, practice, finance, market AI, morale, form, scout eval).
- Files: `src/modules/calendar/calendar_service.py`, `src/modules/simulation/match_engine_service.py` (post-match block ~1431–1681), `src/modules/career/*`
- Impact: Partial day advances (e.g. standings updated but form/morale skipped) look “OK” to the player; hard to detect broken integrations.
- Fix approach: Structured error counters in API response; fail-fast in tests; critical path (standings, burnout) should not soft-fail.

**Pydantic / docs debt largely cleared, docs stale:**
- Issue: Older reports cite Pydantic v2 `.dict()` / `Config` warnings. Current code uses `model_dump()` (`match_engine_service.py`, `matches.py`) and `SettingsConfigDict` (`config.py`). No `.dict()` / legacy `class Config` found under `src/`.
- Files: `docs/RELATORIO_ESTADO_ATUAL.md` (stale debt list), actual code already modernized
- Impact: Planners may chase fixed issues; trust of docs erodes.
- Fix approach: Treat this CONCERNS.md + code as source of truth; refresh RELATORIO when planning.

## Known Bugs

**Redis client treats non-localhost URLs as Mock:**
- Symptoms: With `REDIS_URL=redis://redis:6379` (Docker service name), client sets `_is_mock = True` because `"localhost" not in settings.redis_url`, never connects to real Redis.
- Files: `src/core/redis_client.py` lines 59–65 (`RedisClient.__init__` / `connect`)
- Trigger: Any redis URL without the substring `localhost`, or connection failure (falls back to Mock with a warning).
- Workaround: Use `redis://localhost:6379` from host; set URL exactly to `"mock"` only when intentional.
- Fix: `_is_mock = redis_url in ("mock", "memory", "")`; attempt real client for all `redis://` / `rediss://` URLs.

**Possible double fatigue on managed match days:**
- Symptoms: Manager starters may take MATCH_DAY fatigue twice — once in `BurnoutService.process_end_of_day` when advancing the day (`is_match_day=True` for all teams), and again when live match ends in `MatchEngineService` (+5 burnout / +12 visual / +8 mental).
- Files: `src/modules/calendar/calendar_service.py` (end-of-day burnout loop), `src/modules/calendar/burnout_service.py`, `src/modules/simulation/match_engine_service.py` (~1578–1608)
- Trigger: Advance into/through match day, then complete live match for managed team.
- Workaround: None in UI; playtest may see inflated burnout vs AI-only teams (AI auto-sim path may not double-apply the same way).
- Fix: Skip MATCH_DAY starter load for teams with pending live match, or apply fatigue only once at match resolution for all teams that actually played.

**Live match duration / default speed:**
- Symptoms: Default live speed is **2x** (`StartLiveMatchRequest.speed = "2x"` → 1000 ms/tick × ~40 min ≈ **40s** wall clock). **1x** is 2000 ms/tick (~80s). Loop always runs up to 40 minutes of game time with `asyncio.sleep` between ticks unless `instant`.
- Files: `src/modules/simulation/match_engine_service.py` (`LIVE_SPEED_PRESETS`, `_run_simulation_loop`), `src/api/schemas.py`, FE `MatchSimulation` polling
- Trigger: Starting live without changing speed; long sessions if stuck at 1x.
- Workaround: Use `POST /matches/live/{id}/speed` with `4x` or `instant`.
- Fix: Default to `4x` or `instant` for non-showcase; support skip-to-end; reduce Redis read/write per tick (currently reloads full state every minute).

**asyncio.create_task fire-and-forget live loop:**
- Symptoms: Live simulation task is not tracked/cancelled on disconnect; process restart aborts mid-match without cleanup; concurrent state updates rely on full-state Redis rewrite races.
- Files: `src/modules/simulation/match_engine_service.py` (`start_live_simulation` → `asyncio.create_task`)
- Trigger: Server restart, overlapping start for same match_id, rapid speed changes.
- Workaround: Prefer finishing match or using instant before restart.
- Fix: Task registry + cancel on shutdown; optimistic version field on `LiveMatchState`.

**Save UUID hard-coupling to seed instance:**
- Symptoms: After force reseed, load fails or mutates wrong entities because player/team IDs changed.
- Files: `src/modules/career/save_service.py` (load applies by UUID; warns only on `seed_tag`)
- Trigger: `force=true` seed or new career reseed, then load old slot.
- Workaround: Delete obsolete saves; start new career after reseed.
- Fix: Stronger seed fingerprint; refuse load on team UUID missing; optional remap by abbreviation (partial).

## Security Considerations

**No authentication on any API surface:**
- Risk: Any client on the network can seed/drop DB, transfer players, advance calendar, fire staff, delete saves, start matches.
- Files: All routers under `src/api/routes/*`; `src/main.py` (no auth middleware); `secret_key` in `src/core/config.py` is unused for auth
- Current mitigation: Local-only expectation (dev prototype); single-user design documented as out of scope for multiplayer
- Recommendations: Keep bound to `127.0.0.1` in launcher; before any LAN/cloud deploy add session token or disable destructive routes (`/db/seed`, force reseed) outside debug

**CORS wide open:**
- Risk: `allow_origins=["*"]` with `allow_credentials=True` (`src/main.py`) — browser any-origin access to API.
- Files: `src/main.py`
- Current mitigation: Localhost usage
- Recommendations: Restrict to Vite origin (`http://localhost:5173`) when leaving pure local demo

**Hardcoded infrastructure secrets in compose:**
- Risk: `docker-compose.yml` embeds `POSTGRES_PASSWORD: lol_secret` and default admin user. Acceptable for local demo, unsafe if reused.
- Files: `docker-compose.yml`, `src/core/config.py` (`secret_key` default `"dev-secret-key"`)
- Current mitigation: Dev-only compose; `.env` for app URLs (do not commit secrets — never read `.env` contents in tooling)
- Recommendations: Env-file substitution for compose passwords; rotate defaults in any shared environment

**Destructive endpoints without confirmation gate at protocol level:**
- Risk: `POST /db/seed?force=true` and `POST /career/new` with default reseed wipe data; no auth, only query/body flag.
- Files: `src/api/routes/seed.py`, `src/api/routes/career.py`
- Current mitigation: Seed skip when already seeded; FE wizard is intentional destructive path
- Recommendations: Require `Confirm: true` header + debug mode for force seed; never expose force in production profile

## Performance Bottlenecks

**Live match tick loop I/O:**
- Problem: Each game minute may sleep, then `get_generic` full state, re-parse `LiveMatchState`, simulate, `set_generic` full state (JSON). Post-match opens new DB work (morale, org, playoffs, scout, training XP, form) inside same service.
- Files: `src/modules/simulation/match_engine_service.py` (`_run_simulation_loop`, persistence block)
- Cause: Sleep-based real-time design + full-document Redis rewrite + heavy post-match side effects
- Improvement path: Keep state in process memory with periodic flush; batch Redis writes; default faster speeds; pure simulate_n_minutes for skip

**Calendar advance fans out many services:**
- Problem: One day advance runs burnout for all teams, training, scouting, practice, org board, finance month tick, market AI, patch transition, optional auto-sim of all non-managed matches (draft AI + MatchEngine each).
- Files: `src/modules/calendar/calendar_service.py`
- Cause: Sequential async pipeline with N teams × services; auto-sim does full snake draft per match
- Improvement path: Cache champion/meta for auto-sim; parallelize independent team processors carefully (single DB session limits); lighter auto-sim mode

**Frontend monolith re-renders:**
- Problem: Single Zustand store holds hub + draft + live + market; large screens (`TacticsDraft`, `MatchSimulation`, `Dashboard`) subscribe broadly.
- Files: `frontend/src/store/useGameStore.ts`, `frontend/src/screens/*`
- Cause: No domain slices; live polling updates large state trees
- Improvement path: Selectors/shallow compare; split stores; throttle live poll

**Champion image CDN dependency:**
- Problem: Portraits/splash from Riot Data Dragon (network). Offline or rate limits degrade UI.
- Files: `frontend/src/lib/champions.ts`, `ChampionImage` component
- Cause: External CDN as runtime dependency
- Improvement path: Local cache or fallbacks already partially used for player photos under `frontend/public/players/`

## Fragile Areas

**MatchEngineService post-match side-effect hub:**
- Files: `src/modules/simulation/match_engine_service.py` (end of simulation: standings, MoraleService, OrgService, PlayoffService, ScoutSessionService, TrainingService, StaffService, FormService)
- Why fragile: One method owns competition + career integrity; any exception is partially swallowed; order of burnout vs calendar day matters
- Safe modification: Add new post-match hooks as pure services with unit tests; do not inline more logic into the tick loop
- Test coverage: `tests/test_match_engine_service.py`, `test_live_speed.py`, form/morale tests exist — integration of full live→standings→playoff chain is thinner

**CalendarService as career orchestrator:**
- Files: `src/modules/calendar/calendar_service.py`
- Why fragile: Imports nearly every career module; managed_team_id branching; auto-sim vs pending match
- Safe modification: New day-of-week effects as separate `process_*` functions with dedicated tests; avoid new Redis key prefixes without save patterns
- Test coverage: Week calendar, fatigue, playoffs, market window, offseason tests — full advance integration via `tests/test_api_integration.py` / sprint tests

**Zustand store + API client contract:**
- Files: `frontend/src/store/useGameStore.ts`, `frontend/src/services/api.ts`, `src/api/serializers.py`
- Why fragile: Snake/camel mapping and optional fields; deprecated `lastAutoResults` kept for compat; large imperative flows (new career, advance day, live)
- Safe modification: Type API responses; extend `hubAlerts` pure tests for new hub KPIs; avoid silent `any`
- Test coverage: **No store or screen tests** — only pure libs (see Test Coverage Gaps)

**Draft FE sequence vs backend DraftAI:**
- Files: `frontend/src/screens/TacticsDraft.tsx` (local `DRAFT_SEQUENCES`), `src/modules/draft/snake_draft.py`, `src/api/routes/draft.py`
- Why fragile: Sequence and role assignment can drift from backend snake; opponent turns call `/draft/ai-decision` but FE owns turn machine
- Safe modification: Single source of truth for action order (API returns expected action each turn)
- Test coverage: Backend draft AI/analyzer/scout tests; FE draft untested

**Schema evolution on SQLite file DB:**
- Files: `lol_manager.db`, `src/main.py` bootstrap, models under `src/models/*`
- Why fragile: create_all does not alter existing tables; only one hand-rolled column migrate
- Safe modification: Always add Alembic revision + bootstrap path for SQLite
- Test coverage: Tests use temp SQLite (`tests/conftest.py`) — does not catch production file drift

## Scaling Limits

**Single-process in-memory Redis + live tasks:**
- Current capacity: One local player, one uvicorn worker, one live match task
- Limit: Multi-worker or multi-user loses shared MockRedis; two live matches stress asyncio sleep loops
- Scaling path: Real Redis + sticky sessions or shared state; cap concurrent live sims; prefer batch sim for AI matches

**SQLite write contention:**
- Current capacity: Fine for single-user career
- Limit: Concurrent writers (live post-match + calendar advance) can lock; not multi-tenant
- Scaling path: Postgres (`asyncpg` already in deps) via `database_url` / docker-compose

**Career systems in Redis keyspace:**
- Current capacity: 8 CBLOL teams, one league
- Limit: Key proliferation (`career:form:player:{id}`, scouting knowledge, etc.) without TTL on Mock; export_snapshot uses KEYS-style listing
- Scaling path: Real Redis SCAN; namespace by save slot / career id

## Dependencies at Risk

**External Riot Data Dragon (runtime UI):**
- Risk: CDN/path changes or offline play break champion art
- Impact: Draft/live immersion degraded
- Migration plan: Vendor critical assets or pin versioned DDragon path in `frontend/src/lib/champions.ts`

**Python 3.12 + Poetry stack vs documented 3.11 pyc:**
- Risk: Workspace shows `cpython-311` pycache while `pyproject.toml` requires `python = "^3.12"` — environment mismatch risk on contributors’ machines
- Impact: Subtle install/runtime differences
- Migration plan: Pin one Python version in README/`run_game.bat` and CI

**FastAPI/Pydantic major versions:**
- Risk: Stack is on Pydantic v2 / FastAPI 0.111 — keep using `model_dump` / Settings v2; avoid reintroducing v1 APIs
- Impact: Deprecation noise if old patterns return
- Migration plan: Lint for `.dict(` / `orm_mode` in CI

**docker-compose Postgres/Redis unused by default launcher:**
- Risk: `run_game.bat` starts SQLite + MockRedis path only; compose stack can drift untested
- Impact: “Production prepared” path is theoretical
- Migration plan: Document dual profiles; smoke-test compose occasionally

## Missing Critical Features

**Auth / multi-user / cloud save:**
- Problem: Explicitly out of product scope for now, but blocks any shared deployment
- Blocks: Online career, anti-cheat of economy, multi-manager leagues

**Mid-match resume after process restart:**
- Problem: Live state only in Redis memory; not in save blob
- Blocks: Reliable long play sessions with reboots

**Cláusulas ricas / facility tree / Desafiante (product backlog):**
- Problem: Documented gaps MK-2, OR-3, tier-2 league (`docs/PLANO_MELHORIAS_SISTEMAS.md`, `docs/HANDOFF_SESSAO.md`)
- Blocks: Deep contract/org gameplay — not infra bugs, but product depth limits

**Tutorial / i18n / sound:**
- Problem: Intentionally deferred
- Blocks: Onboarding for non-dev players

## Test Coverage Gaps

**Frontend screens, store, and API client:**
- What's not tested: `useGameStore` flows (advance day, new career, live poll), all `screens/*`, `services/api.ts` HTTP mapping, draft UI sequence
- Files: `frontend/src/store/useGameStore.ts`, `frontend/src/screens/*`, `frontend/src/services/api.ts`
- Risk: Contract breaks between backend serializers and FE go unnoticed until playtest; `run_game.bat` runs `npm run build` but **not** `npm test`
- Priority: **High**

**Frontend pure-lib coverage is partial only:**
- What's tested: `frontend/src/lib/riftMap.test.ts`, `hubAlerts.test.ts`, `orgBrands.test.ts` (Vitest configured in `frontend/vitest.config.ts`)
- What's not: `champions.ts`, `playerPhotoMap.ts`, most components
- Priority: **Medium**

**Live full pipeline integration:**
- What's not tested: Start live → N ticks → standings + playoff series + form + double-burnout scenarios end-to-end
- Files: `src/modules/simulation/match_engine_service.py`, `src/api/routes/matches.py`
- Risk: Post-match career integrity regressions
- Priority: **High**

**Save/load Redis career round-trip edge cases:**
- What's partially tested: `tests/test_sprint_g.py` (export/import snapshot), `tests/test_career_save.py`
- Gaps: load after force reseed; missing calendar key; corrupted partial JSON; mid-match exclusion behavior
- Priority: **Medium**

**Seed force / new career destructive path:**
- What's tested: `tests/test_new_career.py` with force_reseed
- Gaps: Concurrent seed, API abuse without force when empty vs seeded matrix for all routes
- Priority: **Low–Medium**

**Security / config:**
- What's not tested: CORS, binding, force-seed guards
- Priority: **Low** while local-only; **High** before network exposure

---

## Coupling Map (systems that must stay consistent)

| Change in… | Also verify… |
|------------|----------------|
| Redis key prefix | `flush_game_state`, `CAREER_REDIS_PATTERNS`, save export/import |
| Match end stats | Standings, playoffs, morale, org, form, training XP, burnout |
| Calendar day types | Burnout deltas, training, scouting, practice, market AI |
| Seed team UUIDs | All saves, FE cached team ids, new career by abbreviation |
| Draft action order | `snake_draft.py` + `TacticsDraft.tsx` sequence |
| Live state shape | `MatchSimulation.tsx`, `riftMap.ts`, serializers |

---

## Priority Fix Shortlist (for planners)

1. **High — Redis mock detection + document real Redis** (`src/core/redis_client.py`)  
2. **High — Double fatigue audit** (calendar MATCH_DAY vs live post-match)  
3. **High — FE tests in `run_game.bat` + store/API contract tests**  
4. **Medium — Include or explicitly forbid mid-match save; surface UI**  
5. **Medium — Split `MatchEngineService` post-match pipeline**  
6. **Medium — Bind API to localhost; lock force seed behind debug**  
7. **Low — Align dual match engines; expand Alembic-only migrations**

---

*Concerns audit: 2026-07-17*
