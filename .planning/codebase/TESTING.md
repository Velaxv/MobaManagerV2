# Testing Patterns

**Analysis Date:** 2026-07-17

## Test Framework

### Backend

**Runner:**
- pytest `^8.2.0` (dev dependency in `pyproject.toml`)
- pytest-asyncio `^0.23.7` with `asyncio_mode = "auto"` under `[tool.pytest.ini_options]`
- httpx `^0.27.0` for ASGI integration tests

**Config:** `pyproject.toml`
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

**Assertion Library:**
- pytest built-in `assert`
- `pytest.raises(...)` for expected errors

**Run Commands:**
```bash
# From repo root (PYTHONPATH=.)
python -m pytest tests -q --tb=short

# Single file
python -m pytest tests/test_training.py -q

# Single test
python -m pytest tests/test_market_window.py::test_window_playoffs_closed -q

# Verbose failures
python -m pytest tests -vv --tb=short
```

**CI (`.github/workflows/ci.yml`):**
```bash
python -m pytest tests -q --tb=short
```
Env in CI: `DATABASE_URL=sqlite+aiosqlite:///./ci_test.db`, `REDIS_URL=mock`, `PYTHONPATH=.`

### Frontend

**Runner:**
- Vitest `^3.2.7`
- Config: `frontend/vitest.config.ts`
- Environment: `node` (not jsdom/happy-dom)
- Include: `src/**/*.{test,spec}.{ts,tsx}`
- Plugin: `@vitejs/plugin-react`

**Assertion Library:**
- Vitest `expect` from `'vitest'`

**Run Commands:**
```bash
cd frontend
npm test              # vitest run (CI-style once)
npm run test:watch    # vitest watch
```

**CI note:** GitHub Actions currently runs `npm run build` for frontend — **not** `npm test`. Run Vitest locally when changing `frontend/src/lib/*`.

## Test File Organization

### Backend

**Location:** dedicated `tests/` at repo root (not co-located with `src/`)

**Naming:** `test_<domain>.py`

**Inventory (33 files):**
| File | Focus |
|------|--------|
| `tests/conftest.py` | Shared fixtures (`api_client`) |
| `tests/test_api_integration.py` | Full HTTP flows via ASGI |
| `tests/test_math_utils.py` | Pure math helpers |
| `tests/test_match_engine.py` | Simulation engine with MockTeam |
| `tests/test_match_engine_service.py` | Live match service |
| `tests/test_match_depth.py` | Chemistry, towers, MVP ratings |
| `tests/test_live_speed.py` | Live speed presets |
| `tests/test_draft_ai.py` | Snake draft + AI |
| `tests/test_draft_scout.py` | Scout advice + sessions |
| `tests/test_draft_analyzer.py` | Comp analysis |
| `tests/test_training.py` | CA development |
| `tests/test_fatigue_recovery.py` | Burnout/rest loads |
| `tests/test_finance.py` | Payroll math |
| `tests/test_market_window.py` | Transfer window rules |
| `tests/test_transfer_negotiation.py` | Transfers |
| `tests/test_academy.py` | Lineup / promote-demote |
| `tests/test_scouting.py` | Scouting knowledge |
| `tests/test_staff_service.py` | Staff hire/fire |
| `tests/test_org_service.py` | Board/org goals |
| `tests/test_form_and_staff_powers.py` | Form + coach powers |
| `tests/test_morale_practice.py` | Morale/practice |
| `tests/test_career_save.py` | Save slot paths/meta |
| `tests/test_new_career.py` | New career HTTP |
| `tests/test_offseason.py` | Offseason flows |
| `tests/test_playoffs.py` / `test_playoff_series.py` | Playoffs |
| `tests/test_round_robin.py` / `test_round_results.py` | Schedule results |
| `tests/test_week_calendar.py` | Week calendar |
| `tests/test_patch_service.py` / `test_global_meta.py` | Patches/meta |
| `tests/test_tactics.py` | Tactics |
| `tests/test_sprint_g.py` / `test_sprint_h.py` | Feature-sprint bundles |

**Structure:**
```
tests/
├── conftest.py          # api_client, anyio_backend
└── test_*.py            # one domain / feature area per file
```

### Frontend

**Location:** co-located with pure modules under `frontend/src/lib/`

**Files:**
- `frontend/src/lib/hubAlerts.test.ts`
- `frontend/src/lib/orgBrands.test.ts`
- `frontend/src/lib/riftMap.test.ts`

**Naming:** `<module>.test.ts` beside `<module>.ts`

**Not tested (current):** React screens/components (`screens/`, `components/`), Zustand store, `services/api.ts` — no DOM/RTL setup.

## Test Structure

### Backend unit (sync pure / service logic)

```python
"""Testes do sistema de treino / desenvolvimento CA→PA."""

from unittest.mock import AsyncMock
import pytest
from src.modules.career.training_service import TrainingService, normalize_focus

def test_normalize_focus_and_intensity():
    assert normalize_focus("mechanics") == "MECHANICS"
    assert normalize_focus("nope") == "BALANCED"

def test_develop_player_can_gain_ca(monkeypatch):
    svc = TrainingService(db=AsyncMock())
    player = _make_player(ca=100, pa=150)
    monkeypatch.setattr(
        "src.modules.career.training_service.random.random",
        lambda: 0.0,
    )
    result = svc._develop_player(player, day_mult=1.0, focus="BALANCED", ...)
    assert result["ca_delta"] == 1
```

### Backend async service with mocks

```python
from unittest.mock import AsyncMock, MagicMock
import pytest

@pytest.mark.asyncio
async def test_window_playoffs_closed():
    league = MagicMock(current_phase=SplitPhase.PLAYOFFS)
    svc = MarketWindowService(MagicMock())
    svc.get_league = AsyncMock(return_value=league)
    with pytest.raises(ValueError, match="fechada"):
        await svc.assert_can_buy_from_clubs("team-id")
```

### Backend integration (HTTP)

```python
"""Testes de integração da API (httpx + ASGI)."""
from __future__ import annotations
import pytest

pytestmark = pytest.mark.asyncio

async def _seed(client):
    r = await client.post("/db/seed?force=true")
    assert r.status_code == 201, r.text
    return r.json()

async def test_seed_advance_standings_flow(api_client):
    seed = await _seed(api_client)
    team_id = seed["teams"].get("PNG") or list(seed["teams"].values())[0]
    r = await api_client.post(f"/calendar/advance?managed_team_id={team_id}")
    assert r.status_code == 200, r.text
```

**Patterns:**
- Module docstring describes what is covered
- Helper factories: `_make_player`, `_seed`, local `MockPlayer`/`MockTeam` classes
- Prefer `assert r.status_code == 200, r.text` so failures show response body
- `tmp_path` + `monkeypatch` for filesystem isolation (saves)

### Frontend unit (Vitest)

```typescript
import { describe, expect, it } from 'vitest'
import { buildHubAlerts, badgeForScreen } from './hubAlerts'

describe('buildHubAlerts', () => {
  it('prioriza critical sobre warning', () => {
    const alerts = buildHubAlerts({
      burnoutCount: 1,
      matchPending: true,
      matchLive: false,
      financeHealth: 'warning',
    })
    expect(alerts[0].level).toBe('critical')
  })
})
```

**Patterns:**
- Group by function with `describe`
- Portuguese or English `it(...)` descriptions — match nearby tests
- Import only from pure modules; no React render

## Mocking

### Backend

**Framework:** `unittest.mock` (`MagicMock`, `AsyncMock`, `patch`) + pytest `monkeypatch`

**Shared integration fixture (`tests/conftest.py`):**
- Builds temp SQLite (`tmp_path / "integration.db"`)
- `monkeypatch.setattr` on `src.core.database.engine`, `AsyncSessionLocal`, seed module, match engine service
- Overrides FastAPI `get_db` dependency
- Uses in-memory **MockRedis** via `redis_client.connect()` and clears `_store`
- Yields `httpx.AsyncClient` with `ASGITransport(app=app)`
- Cleans `app.dependency_overrides` and disposes engine after test

**Service unit mocks:**
```python
svc = MoraleService(MagicMock())
svc.get_state = AsyncMock(return_value=dict(DEFAULT_STATE, team_id="t1"))
svc.save_state = AsyncMock()
```

**Lightweight domain doubles:**
- `MockPlayer` / `MockTeam` / `MockStaff` classes inside draft/match tests — duck-typed for engine APIs (`get_starters`, `get_champion_pool_tier`)
- `types.SimpleNamespace` for partial player objects (`tests/test_training.py`)

**What to Mock:**
- `AsyncSession` / DB when testing pure service rules
- Redis-backed state when unit-testing without infrastructure
- `random.random` / RNG for deterministic CA rolls
- Filesystem via `tmp_path` + monkeypatch of `saves_dir`

**What NOT to Mock:**
- Pure math (`src/shared/math_utils.py`) — call real functions
- Snake draft / counter tables when asserting real game rules
- Prefer real seed + SQLite for end-to-end API flows (`api_client`)

### Frontend

**Framework:** Vitest (no `vi.mock` usage in current tests)

**Pattern:** pure function tests with fixture objects inline — no network, no store mocks.

## Fixtures and Factories

### Backend shared fixtures

| Fixture | Scope | Purpose |
|---------|-------|---------|
| `api_client` | function (async) | Isolated ASGI client + SQLite + MockRedis |
| `anyio_backend` | function | Returns `"asyncio"` |
| `mock_teams` | local per file | Strong vs weak teams for engine/draft |

**Factory pattern (inline helpers):**
```python
def _make_player(*, ca=120, pa=160, age_years=20, role=PlayerRole.MID, name="TestMid"):
    return SimpleNamespace(
        id="p1",
        name=name,
        role=role,
        current_ability=ca,
        potential_ability=pa,
        # ...
        get_age=lambda self=None, y=age_years: y,
    )
```

**Seed pattern for integration:**
```python
r = await client.post("/db/seed?force=true")
# Expect 8 CBLOL teams; use abbreviation map seed["teams"]["PNG"]
```

### Frontend fixtures

- Inline object literals in each `it` block
- Shared constants from modules under test (`ALL_ORG_BRANDS`, `RIFT_STRUCTURE_DEFS`)

**Location:** no `tests/fixtures/` package — keep helpers private to the test file unless reused (then add to `conftest.py`)

## Coverage

**Requirements:** None enforced (no pytest-cov, no Vitest coverage thresholds in config)

**View Coverage (optional local):**
```bash
# Backend (if pytest-cov installed)
python -m pytest tests --cov=src --cov-report=term-missing

# Frontend
cd frontend && npx vitest run --coverage
```

**Practical expectation:**
- New game-rule logic in `src/modules/**` should get a `tests/test_*.py` case
- New pure FE helpers in `frontend/src/lib/` should get a co-located `*.test.ts`
- Screens/UI remain manual / build-checked unless a lib extract is made

## Test Types

**Unit Tests (primary backend style):**
- Pure functions: math, counters, narration, normalizers
- Service methods with AsyncMock DB
- Engine simulation with MockTeam lineups
- Save path validation without real career DB

**Integration Tests:**
- `tests/test_api_integration.py` and selected career/live tests using `api_client`
- Full path: seed → calendar advance → standings / training / patches / match
- Isolated from developer `lol_manager.db` via temp SQLite

**E2E Tests:**
- Not used (no Playwright/Cypress)
- Closest equivalent: API integration + manual frontend against local FastAPI

## Common Patterns

### Async testing

```python
import pytest

@pytest.mark.asyncio
async def test_live_match_initialization():
    ...

# Or module-wide:
pytestmark = pytest.mark.asyncio
```

With `asyncio_mode = "auto"`, async tests are collected without explicit markers in many cases; markers remain common for clarity.

### Error testing

```python
with pytest.raises(ValueError):
    weighted_average([10], [1, 2])

with pytest.raises(ValueError, match="fechada"):
    await svc.assert_can_buy_from_clubs("x")
```

Frontend:
```typescript
expect(parseLocationFromEvent(null)).toBeNull()
expect(getOrgBrand(null).primary).toBeTruthy()
```

### Determinism

- `np.random.default_rng(seed=42)` for stochastic math
- Monkeypatch `random.random` for training rolls
- Seed endpoint with `force=true` for clean DB state
- Assert ranges/probabilities with tolerances (`abs(x - 0.5) < 1e-6`) rather than exact floats when noise exists

### HTTP assertions

```python
assert r.status_code == 201, r.text
data = r.json()
assert data.get("team_count") == 8
assert "id" in teams[0]
```

### Adding a new backend test

1. Prefer unit test in `tests/test_<feature>.py` without `api_client` if no HTTP contract
2. Use `Mock*` / `SimpleNamespace` / `AsyncMock` for dependencies
3. For API contracts, add async test using `api_client` and `_seed`
4. Keep Portuguese messages in `match=` only when asserting user-facing errors

### Adding a new frontend test

1. Extract pure logic into `frontend/src/lib/<name>.ts` if currently inline in a screen
2. Add `frontend/src/lib/<name>.test.ts`
3. Use Vitest `describe`/`it`; keep environment free of DOM assumptions
4. Run `npm test` from `frontend/`

### What CI enforces

| Job | Command | Covers |
|-----|---------|--------|
| Backend | `python -m pytest tests -q --tb=short` | All backend tests |
| Frontend | `npm run build` (`tsc -b && vite build`) | Typecheck + bundle only |

Frontend unit tests are **not** in CI yet — treat them as required local gate when editing `lib/`.

---

*Testing analysis: 2026-07-17*
