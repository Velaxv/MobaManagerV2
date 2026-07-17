# Coding Conventions

**Analysis Date:** 2026-07-17

## Naming Patterns

**Python files:**
- `snake_case.py` for modules: `finance_service.py`, `match_engine.py`, `calendar_helpers.py`
- Tests: `test_<area>.py` under `tests/` (e.g. `tests/test_training.py`, `tests/test_api_integration.py`)
- Package init: `__init__.py` in every package under `src/`

**TypeScript/React files:**
- Components/screens: `PascalCase.tsx` — `HubPageHeader.tsx`, `MatchSimulation.tsx`, `GameShell.tsx`
- Utilities/libs: `camelCase.ts` — `hubAlerts.ts`, `orgBrands.ts`, `riftMap.ts`, `playerPhotoMap.ts`
- Store: `useGameStore.ts` (Zustand hook prefix)
- API client: `api.ts` under `frontend/src/services/`
- Types: `game.ts`, `screens.ts` under `frontend/src/types/`
- Co-located tests: `<module>.test.ts` next to source (e.g. `hubAlerts.test.ts`)

**Python functions / methods:**
- `snake_case`: `get_snapshot`, `process_monthly_tick_for_team`, `normalize_focus`
- Private helpers: leading underscore `_load_team`, `_develop_player`, `_sqlite_bootstrap`
- Async route handlers: `async def get_teams(...)`, `async def get_team_finance(...)`
- Test functions: `test_<behavior>` or `async def test_<behavior>`

**TypeScript functions:**
- `camelCase`: `buildHubAlerts`, `mapApiPlayer`, `parseLocationFromEvent`, `getOrgBrand`
- API methods on `api` object: `getTeams`, `getTeamFinance`, `setTeamTraining`
- React components: `PascalCase` function exports — `export function HubPageHeader(...)`

**Variables:**
- Python: `snake_case` (`team_id`, `monthly_salary`, `burnout_meter`)
- TypeScript: `camelCase` (`teamId`, `burnoutCount`, `matchPending`)
- Constants: `UPPER_SNAKE` — `ACTIVE_STATUSES`, `MONTH_DAYS`, `FOCUSES`, `API_BASE`, `DRAFT_ORDER`
- Logger names: `logging.getLogger(__name__)` in services; app-wide `logging.getLogger("lol_manager_api")` in routes/`main.py`

**Types / classes:**
- Python classes: `PascalCase` — `FinanceService`, `MatchEngine`, `Player`, `LolManagerException`
- Service pattern: `<Domain>Service` with `__init__(self, db: AsyncSession)`
- Pydantic request DTOs: `<Action>Request` — `CreateMatchRequest`, `HireStaffRequest`, `NewCareerRequest` in `src/api/schemas.py`
- SQLAlchemy models: singular domain noun — `Player`, `Team`, `Match` in `src/models/`
- Enums: `PascalCase` class, `UPPER_SNAKE` members — `PlayerRole.TOP`, `SplitPhase.REGULAR_SEASON` in `src/shared/enums.py`
- TypeScript: `interface`/`type` in `PascalCase` — `ApiPlayer`, `HubAlert`, `AppScreen`
- Const-object enums (erasableSyntaxOnly-safe):
  ```typescript
  export const PlayerRole = { TOP: "TOP", ... } as const;
  export type PlayerRole = typeof PlayerRole[keyof typeof PlayerRole];
  ```
  Use this pattern in `frontend/src/types/game.ts` — do **not** use TypeScript `enum` keywords.

## Code Style

**Formatting:**
- No Black/Ruff/Prettier config detected in repo
- Python: 4-space indent; double quotes common; module docstrings at top of files
- TypeScript: 2-space indent; single quotes in Vitest tests; mix of single/double in app code — match the file you edit
- Prefer trailing commas in multi-line TS object/array literals (existing Vitest tests)

**Linting:**
- Frontend: **oxlint** via `npm run lint` (`frontend/package.json`)
- TypeScript strict-ish via `frontend/tsconfig.app.json`:
  - `noUnusedLocals`, `noUnusedParameters`
  - `erasableSyntaxOnly` (no `enum`, no parameter properties that emit)
  - `verbatimModuleSyntax` — use `import type` for type-only imports
  - `jsx: "react-jsx"`, `moduleResolution: "bundler"`
- Backend: no dedicated linter config; rely on pytest + type hints

**Language / docs:**
- Domain comments and user-facing API error strings are often **Portuguese** (`"Time não encontrado."`, `"Orçamento insuficiente..."`)
- Code identifiers are **English** (`team_id`, `burnout_meter`, `FinanceService`)
- Module docstrings describe rules/MVP behavior at file top (see `src/modules/career/finance_service.py`, `training_service.py`)

## Import Organization

**Python order (typical):**
1. `from __future__ import annotations` (when used — preferred in new modules)
2. Stdlib (`logging`, `uuid`, `json`, `typing`)
3. Third-party (`fastapi`, `sqlalchemy`, `pydantic`, `numpy`, `pytest`)
4. Local `src.*` absolute imports (`from src.models.player import Player`)

**Patterns:**
- Prefer absolute imports from `src.`: `from src.shared.enums import PlayerRole`
- Lazy/local imports inside functions for heavy or circular deps (common in routes):
  ```python
  from src.modules.career.finance_service import FinanceService
  ```
- `TYPE_CHECKING` blocks for ORM relationship type hints (`src/models/player.py`)

**TypeScript order (typical):**
1. React / external packages (`react`, `zustand`, `lucide-react`, `vitest`)
2. Internal relative imports (`../types/game`, `../services/api`, `./riftMap`)
3. `import type { ... }` for types when only used as types (`verbatimModuleSyntax`)

**Path aliases:**
- Not detected — use relative paths (`../lib/...`, `./components/...`)

## Error Handling

**Domain exceptions (`src/shared/exceptions.py`):**
- All custom errors inherit `LolManagerException(message, code=...)`
- Subclasses set a stable `code` string (`PLAYER_AGE_VIOLATION`, `INSUFFICIENT_BUDGET`, etc.)
- Prefer structured fields on the exception (`player_name`, `required_amount`) when useful for callers
- Use when encoding **game-rule** violations

**Service layer:**
- Raise `ValueError("…")` for missing entities / invalid operations (Portuguese messages)
- Routes convert `ValueError` → `HTTPException(status_code=404|400, detail=str(e))`
- Unexpected errors: `logger.error(..., exc_info=True)` then `HTTPException(500, detail=...)`

**API routes:**
```python
try:
    return await FinanceService(db).get_snapshot(team_id)
except ValueError as e:
    raise HTTPException(status_code=404, detail=str(e))
```

**Frontend API client (`frontend/src/services/api.ts`):**
- Central `parseJsonOrThrow(response, fallbackMessage)` — throws `Error` with server detail when `!response.ok`
- Callers in store/screens catch and surface UI state; do not swallow silently for user actions

**Do this:**
- Map domain failures to HTTP status at the route boundary
- Keep services free of FastAPI types (`HTTPException` belongs in `src/api/routes/`)

**Avoid:**
- Bare `except:` without logging
- Returning success payloads for failed operations

## Logging

**Framework:** stdlib `logging`

**Patterns:**
- App bootstrap: `logging.basicConfig(level=INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")` in `src/main.py`
- Routes: `logger = logging.getLogger("lol_manager_api")`
- Services: `logger = logging.getLogger(__name__)`
- Use `logger.info` for lifecycle (startup, Redis connect, seed)
- Use `logger.error(..., exc_info=True)` for unexpected failures in routes
- Use `logger.warning` for degraded modes (e.g. Redis fallback in `src/core/redis_client.py`)

## Comments

**When to comment:**
- Module-level docstring with domain rules / MVP constraints
- Non-obvious game math, calendar alignment, scouting mask behavior
- Inline notes for API contract quirks (`# force=true: testes precisam de seed limpo`)

**JSDoc/TSDoc:**
- Light — short `/** ... */` above exported helpers (`buildHubAlerts`, `HubPageHeader`)
- Prefer clear names over heavy docblocks for simple props

**Python docstrings:**
- Public functions often use Google-ish Args/Returns (see `src/shared/math_utils.py`)
- Exception classes document when they fire and example rules

## Function Design

**Size:**
- Keep pure math/helpers small and testable (`clamp`, `normalize_focus`, `lane_counter_edge`)
- Service methods orchestrate DB + rules; extract `_private` helpers for multi-step logic

**Parameters:**
- Services take `db: AsyncSession` in constructor; methods take domain IDs as `str` or `uuid.UUID`
- Prefer keyword-only flags with `*` when options grow (`serialize_player(..., *, scouting_knowledge=..., apply_scouting_mask=False)`)
- Pydantic models for multi-field request bodies (`src/api/schemas.py`)

**Return values:**
- Services return plain `dict` / dataclasses / domain objects — not Response objects
- Serializers produce frontend-ready dicts (`src/api/serializers.py`)
- Async everywhere for DB/Redis I/O; sync pure functions for engine math

## Module Design

**Backend layout conventions:**
| Layer | Location | Responsibility |
|-------|----------|----------------|
| Routes | `src/api/routes/*.py` | HTTP, validation, HTTPException |
| Schemas | `src/api/schemas.py` | Pydantic request DTOs |
| Serializers | `src/api/serializers.py` | Model → JSON (often camelCase for players) |
| Services | `src/modules/<domain>/*_service.py` | Business rules + persistence |
| Models | `src/models/*.py` | SQLAlchemy ORM |
| Shared | `src/shared/` | Enums, math, exceptions, static data |
| Core | `src/core/` | Config, DB engine, Redis |

**Service class pattern:**
```python
class FinanceService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_snapshot(self, team_id: str) -> Dict[str, Any]:
        ...
```

**Router registration:**
- Each route module exports `router = APIRouter(...)`
- `include_routers(app)` in `src/api/routes/__init__.py` registers all routers

**Frontend layout conventions:**
| Layer | Location | Responsibility |
|-------|----------|----------------|
| Screens | `frontend/src/screens/` | Full pages |
| Components | `frontend/src/components/` | Reusable UI |
| Lib | `frontend/src/lib/` | Pure helpers (test here first) |
| Services | `frontend/src/services/api.ts` | HTTP client |
| Store | `frontend/src/store/useGameStore.ts` | Zustand state + mappers |
| Types | `frontend/src/types/` | Shared TS types / const enums |

**Exports:**
- Prefer named exports for components (`export function Squad`)
- `App` uses default export
- API surface: single `export const api = { ... }` object
- No barrel `index.ts` re-export trees required — import concrete files

## API / JSON Naming

**Inconsistent by design — follow serializer/route you touch:**
- **Player payloads** (via `serialize_player`): **camelCase** keys — `teamId`, `currentAbility`, `burnoutMeter`, `isStarter`
- **Many service/route payloads**: **snake_case** — `team_id`, `monthly_revenue`, `current_day`
- **Pydantic request bodies**: **snake_case** fields — `blue_team_id`, `manager_name`
- Frontend maps API → store shapes in `mapApiPlayer` / `mapWeekCalendar` inside `useGameStore.ts`

**When adding a new endpoint:**
1. Prefer matching the nearest existing endpoint’s key style
2. For player-like entities, use camelCase via serializers for FE consistency
3. Update `frontend/src/services/api.ts` types and any store mappers in the same change

## Domain Constants & Enums

- Game enums live in `src/shared/enums.py` as `str, Enum` (Python)
- Mirror values as const objects in `frontend/src/types/game.ts`
- Use UPPER_SNAKE string values across the stack: `"MECHANICS"`, `"HARD"`, `"BLUE"`, `"MATCH_DAY"`
- Normalize free-form input at service boundary (`normalize_focus("mechanics") → "MECHANICS"`)

## Models & Persistence

- Models inherit `Base` + mixins (`UUIDMixin`, `TimestampMixin`) from `src/models/base.py`
- IDs are UUID v4 generated in app (`default=uuid.uuid4`)
- Use `Mapped[...]` + `mapped_column` (SQLAlchemy 2.0 style)
- CheckConstraints on attribute ranges (CA 0–200, attributes 1–20, burnout 0–100)
- Async sessions only: `AsyncSession`, `select()`, `selectinload()`

## React / UI Conventions

- Screen routing is **store-driven**, not React Router — `useGameStore.currentScreen` + switch in `App.tsx`
- Page chrome: `HubPageHeader` + shared CSS classes (`hq-page-header`, `hq-frame`, `panel-enter`)
- Styling: Tailwind utility classes + custom tokens (`text-lol-hq-cyan`, `bg-hq-header`) from `frontend/tailwind.config.js`
- Icons: `lucide-react`
- Visual identity: tech-noir glass, cyan `#22d3ee` + orange `#f97316` + navy/black — see `docs/STYLE_BIBLE.md`
- Keep presentation in screens/components; pure logic in `lib/` for unit tests

## Testing Conventions (summary)

- Backend tests: plain functions named `test_*`, optional `pytestmark = pytest.mark.asyncio`
- Prefer pure unit tests for engine/math; use `api_client` fixture only for HTTP flows
- Frontend tests: Vitest `describe`/`it`/`expect`, co-located with pure modules under `lib/`
- Determinism: seed RNG (`np.random.default_rng(42)`), monkeypatch `random.random`, force seed with `?force=true`

---

*Convention analysis: 2026-07-17*
