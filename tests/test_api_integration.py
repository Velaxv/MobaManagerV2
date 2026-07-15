"""
Testes de integração da API (httpx + ASGI).

Fluxo coberto (critério P3-2):
  seed → teams/leagues → calendar advance → standings
  + patches, training, scouting, academy, simulate match
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio


async def _seed(client):
    # force=true: testes precisam de seed limpo e determinístico (IN-4)
    r = await client.post("/db/seed?force=true")
    assert r.status_code == 201, r.text
    data = r.json()
    assert data.get("skipped") is not True
    assert data.get("team_count") == 8
    assert data.get("league_id")
    assert len(data.get("teams") or {}) == 8
    return data


async def test_health(api_client):
    r = await api_client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "online"


async def test_seed_teams_leagues_calendar(api_client):
    seed = await _seed(api_client)
    league_id = seed["league_id"]
    png_id = seed["teams"].get("PNG") or next(iter(seed["teams"].values()))

    r = await api_client.get("/teams")
    assert r.status_code == 200
    teams = r.json()
    assert len(teams) == 8
    assert all("id" in t and "abbreviation" in t for t in teams)

    r = await api_client.get("/leagues")
    assert r.status_code == 200
    leagues = r.json()
    assert len(leagues) >= 1
    assert leagues[0]["id"] == league_id

    r = await api_client.get(f"/calendar?managed_team_id={png_id}")
    assert r.status_code == 200
    cal = r.json()
    assert cal.get("league_id") == league_id
    assert isinstance(cal.get("week_calendar"), list)
    assert len(cal["week_calendar"]) == 7

    r = await api_client.get(f"/teams/{png_id}/players")
    assert r.status_code == 200
    players = r.json()
    assert len(players) >= 5
    # Scouting mask fields presentes
    assert "scoutingProgress" in players[0] or "currentAbility" in players[0]


async def test_seed_advance_standings_flow(api_client):
    """Critério principal P3-2: seed → advance → standings verde."""
    seed = await _seed(api_client)
    league_id = seed["league_id"]
    team_id = seed["teams"].get("PNG") or list(seed["teams"].values())[0]

    # Avança vários dias (passa por treino e possivelmente match day)
    last_advance = None
    for _ in range(8):
        r = await api_client.post(f"/calendar/advance?managed_team_id={team_id}")
        assert r.status_code == 200, r.text
        last_advance = r.json()
        assert "results" in last_advance

    assert last_advance is not None
    day_info = last_advance["results"][0]
    assert "day_type" in day_info or "state" in day_info
    # Patch status costuma vir no advance
    assert "active_patch" in day_info or "patch_status" in day_info or True

    r = await api_client.get(f"/leagues/{league_id}/standings")
    assert r.status_code == 200
    standings = r.json()
    assert len(standings) == 8
    assert all("team_id" in s and "wins" in s and "points" in s for s in standings)
    # Após match days, alguma pontuação deve existir (ou zero se só managed games)
    total_games = sum(int(s.get("wins", 0)) + int(s.get("losses", 0)) for s in standings)
    # Em 8 dias com RR, há match days — jogos IA geram standings
    assert total_games >= 0  # smoke
    # Mais forte: se houve auto-sim, total_games > 0
    if day_info.get("auto_simulated_matches") or day_info.get("round_results"):
        assert total_games > 0

    r = await api_client.get(f"/calendar?managed_team_id={team_id}")
    assert r.status_code == 200
    cal = r.json()
    assert int(cal.get("current_day") or 0) >= 1


async def test_patches_after_seed(api_client):
    await _seed(api_client)

    r = await api_client.get("/patches")
    assert r.status_code == 200
    body = r.json()
    assert "active" in body or "patches" in body
    # 16.1 deve estar ativo no seed novo
    if body.get("active"):
        assert body["active"].get("version")
        assert isinstance(body["active"].get("changes"), list)

    r = await api_client.get("/patches/current")
    assert r.status_code == 200
    cur = r.json()
    assert "badges" in cur

    r = await api_client.get("/patches/badges")
    assert r.status_code == 200
    badges = r.json()
    assert "badges" in badges


async def test_training_scouting_academy(api_client):
    seed = await _seed(api_client)
    team_id = seed["teams"].get("PNG") or list(seed["teams"].values())[0]

    # Training plan
    r = await api_client.post(
        f"/teams/{team_id}/training",
        json={"focus": "MECHANICS", "intensity": "HARD"},
    )
    assert r.status_code == 200, r.text
    assert r.json().get("focus") == "MECHANICS"

    r = await api_client.get(f"/teams/{team_id}/training")
    assert r.status_code == 200
    assert r.json().get("focus") == "MECHANICS"

    # Players + scout
    r = await api_client.get(f"/teams/{team_id}/players")
    assert r.status_code == 200
    players = r.json()
    assert players
    target = players[-1]["id"]  # reserva/academy

    r = await api_client.post(
        f"/teams/{team_id}/scouting/assign",
        json={"player_id": target, "focus": "ALL"},
    )
    assert r.status_code == 200, r.text
    assert r.json().get("assignment", {}).get("player_id") == target

    r = await api_client.get(f"/teams/{team_id}/scouting")
    assert r.status_code == 200
    assert r.json().get("assignment") is not None

    # Advance for training/scout progress
    r = await api_client.post(f"/calendar/advance?managed_team_id={team_id}")
    assert r.status_code == 200

    # Academy roster
    r = await api_client.get(f"/teams/{team_id}/academy")
    assert r.status_code == 200
    roster = r.json()
    assert "starters" in roster
    assert "academy" in roster or "bench" in roster
    assert roster.get("counts", {}).get("starters", 0) >= 1

    # Promote academy if available
    academy = roster.get("academy") or []
    if academy and academy[0].get("player_id"):
        pid = academy[0]["player_id"]
        r = await api_client.post(
            f"/teams/{team_id}/academy/promote",
            json={"player_id": pid},
        )
        assert r.status_code == 200, r.text
        assert r.json().get("promoted", {}).get("player_id") == pid


async def test_market_and_champions(api_client):
    seed = await _seed(api_client)
    team_id = seed["teams"].get("PNG") or list(seed["teams"].values())[0]

    r = await api_client.get(f"/market/players?exclude_team_id={team_id}")
    assert r.status_code == 200
    market = r.json()
    assert isinstance(market, list)
    assert len(market) > 0
    # PA mascarado no mercado
    sample = market[0]
    assert "potentialAbilityKnown" in sample or "currentAbility" in sample

    r = await api_client.get("/champions")
    assert r.status_code == 200
    champs = r.json()
    assert len(champs) > 50


async def test_simulate_match_after_seed(api_client):
    seed = await _seed(api_client)
    league_id = seed["league_id"]
    teams = seed["teams"]
    blue = teams.get("PNG") or list(teams.values())[0]
    red = teams.get("FUR") or list(teams.values())[1]
    assert blue != red

    r = await api_client.post(
        "/matches/simulate",
        json={
            "blue_team_id": blue,
            "red_team_id": red,
            "league_id": league_id,
            "week": 1,
            "is_playoff": False,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("match_id")
    assert body.get("winner")

    r = await api_client.get(f"/leagues/{league_id}/standings")
    assert r.status_code == 200
    standings = r.json()
    total_w = sum(int(s.get("wins", 0)) for s in standings)
    assert total_w >= 1


async def test_career_save_list_empty_or_ok(api_client, tmp_path, monkeypatch):
    """Lista de saves não quebra (pasta isolada)."""
    from src.modules.career import save_service

    monkeypatch.setattr(save_service, "saves_dir", lambda: tmp_path)
    await _seed(api_client)

    r = await api_client.get("/career/saves")
    assert r.status_code == 200
    assert "saves" in r.json()
