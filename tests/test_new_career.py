"""Nova carreira do zero — reseed + limpa Redis."""

import pytest


@pytest.mark.asyncio
async def test_new_career_resets_progress(api_client):
    """
    Após avançar o calendário, POST /career/new deve voltar a semana 1 / dia 1
    e devolver um team_id válido pela abreviação.
    """
    r = await api_client.post("/db/seed?force=true")
    assert r.status_code in (200, 201)
    seed = r.json()
    png_id = (seed.get("teams") or {}).get("PNG")
    assert png_id

    # Suja o estado (calendário + redis moral)
    for _ in range(2):
        adv = await api_client.post(
            "/calendar/advance",
            params={"managed_team_id": png_id},
        )
        assert adv.status_code < 500

    res = await api_client.post(
        "/career/new",
        json={
            "manager_name": "Test Coach",
            "team_abbreviation": "FUR",
            "force_reseed": True,
        },
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["manager_name"] == "Test Coach"
    assert body["team_abbreviation"] == "FUR"
    assert body["team_id"]
    assert body["week"] == 1
    assert body["day"] == 1
    assert body.get("redis_keys_cleared") is not None

    new_teams = body.get("teams") or {}
    assert "FUR" in new_teams
    assert new_teams["FUR"] == body["team_id"]
    # ID do PNG mudou após reseed
    assert new_teams.get("PNG") != png_id

    cal = await api_client.get(
        "/calendar",
        params={"managed_team_id": body["team_id"]},
    )
    assert cal.status_code == 200
    data = cal.json()
    assert int(data.get("current_week") or 1) == 1
    assert int(data.get("current_day") or 1) == 1


@pytest.mark.asyncio
async def test_new_career_rejects_short_name(api_client):
    r = await api_client.post(
        "/career/new",
        json={"manager_name": "X", "team_abbreviation": "PNG"},
    )
    assert r.status_code == 400
