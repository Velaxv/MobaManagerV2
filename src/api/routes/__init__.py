"""Agrega e registra todos os routers da API."""

from fastapi import FastAPI

from src.api.routes import (
    health,
    seed,
    calendar,
    teams,
    leagues,
    market,
    champions,
    matches,
    draft,
    offseason,
    career,
    patches,
)


def include_routers(app: FastAPI) -> None:
    """Inclui todos os routers no app FastAPI (prefixos já definidos nas rotas)."""
    app.include_router(health.router)
    app.include_router(seed.router)
    app.include_router(calendar.router)
    app.include_router(teams.router)
    app.include_router(leagues.router)
    app.include_router(market.router)
    app.include_router(champions.router)
    app.include_router(matches.router)
    app.include_router(draft.router)
    app.include_router(offseason.router)
    app.include_router(career.router)
    app.include_router(patches.router)
