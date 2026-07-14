"""Testes de academy / promote / demote / lineup."""

from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.modules.career.academy_service import AcademyService
from src.shared.enums import PlayerRole, ContractStatus


def _player(
    pid,
    name,
    role,
    ca=120,
    is_starter=False,
    is_rookie=False,
    contracts=None,
):
    p = SimpleNamespace(
        id=pid,
        name=name,
        role=role,
        current_ability=ca,
        potential_ability=ca + 30,
        is_starter=is_starter,
        is_rookie=is_rookie,
        contracts=contracts or [],
        get_age=lambda: 20,
    )
    return p


def _team(players):
    team = SimpleNamespace(
        id="team-1",
        name="Test Org",
        players=players,
    )

    def get_starters():
        from src.models.team import Team

        # Reusa lógica real via monkeypatch-style: call method unbound
        return Team.get_starters(team)

    team.get_starters = lambda: get_starters()
    return team


def test_get_starters_prefers_is_starter():
    from src.models.team import Team

    a = _player("1", "A", PlayerRole.MID, ca=100, is_starter=False)
    b = _player("2", "B", PlayerRole.MID, ca=90, is_starter=True)
    c = _player("3", "C", PlayerRole.TOP, ca=110, is_starter=True)
    team = SimpleNamespace(players=[a, b, c])
    starters = Team.get_starters(team)
    mid = next(p for p in starters if p.role == PlayerRole.MID)
    assert mid.name == "B"
    top = next(p for p in starters if p.role == PlayerRole.TOP)
    assert top.name == "C"


def test_get_starters_fallback_highest_ca():
    from src.models.team import Team

    a = _player("1", "Low", PlayerRole.BOT, ca=100, is_starter=False)
    b = _player("2", "High", PlayerRole.BOT, ca=140, is_starter=False)
    team = SimpleNamespace(players=[a, b])
    starters = Team.get_starters(team)
    assert len(starters) == 1
    assert starters[0].name == "High"


def test_squad_status_and_rookie_info():
    svc = AcademyService(db=AsyncMock())
    contract = SimpleNamespace(
        status=ContractStatus.ACTIVE,
        has_rookie_clause=True,
        rookie_participation_rate=0.3,
        rookie_games_played=6,
        rookie_total_league_games=20,
        rookie_extension_triggered=False,
    )
    p = _player("1", "Rook", PlayerRole.MID, is_rookie=True, contracts=[contract])
    starters = []
    assert svc._squad_status(p, starters) == "ACADEMY"
    info = svc._rookie_info(p)
    assert info["has_rookie_clause"] is True
    assert info["on_track"] is True
    assert info["participation_rate"] == 0.3


@pytest.mark.asyncio
async def test_promote_swaps_starter():
    svc = AcademyService(db=AsyncMock())
    starter = _player("s1", "Starter", PlayerRole.MID, ca=150, is_starter=True)
    academy = _player("a1", "Academy Kid", PlayerRole.MID, ca=110, is_starter=False, is_rookie=True)
    team = SimpleNamespace(id="00000000-0000-0000-0000-0000000000aa", name="T", players=[starter, academy])

    # Patch Team.get_starters used after promote via get_roster
    async def load(_tid):
        return team

    async def ensure(t):
        return [starter] if starter.is_starter else ([academy] if academy.is_starter else [])

    svc.load_team = load
    svc.ensure_lineup = ensure
    svc.db.commit = AsyncMock()
    svc.db.refresh = AsyncMock()

    # promote needs get_roster which reloads — stub get_roster at end
    async def fake_roster(_tid):
        return {"starters": [], "bench": [], "academy": [], "counts": {}}

    svc.get_roster = fake_roster

    result = await svc.promote(str(team.id), "a1")
    assert academy.is_starter is True
    assert starter.is_starter is False
    assert result["promoted"]["name"] == "Academy Kid"
    assert result["demoted"]["name"] == "Starter"


@pytest.mark.asyncio
async def test_demote_promotes_replacement():
    svc = AcademyService(db=AsyncMock())
    starter = _player("s1", "Starter", PlayerRole.TOP, ca=150, is_starter=True)
    bench = _player("b1", "Bench", PlayerRole.TOP, ca=130, is_starter=False)
    team = SimpleNamespace(id="00000000-0000-0000-0000-0000000000bb", name="T", players=[starter, bench])

    async def load(_tid):
        return team

    async def ensure(t):
        return []

    svc.load_team = load
    svc.ensure_lineup = ensure
    svc.db.commit = AsyncMock()
    svc.get_roster = AsyncMock(return_value={"ok": True})

    result = await svc.demote(str(team.id), "s1")
    assert starter.is_starter is False
    assert bench.is_starter is True
    assert result["promoted"]["name"] == "Bench"
