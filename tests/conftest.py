"""
Fixtures compartilhadas.

Integração HTTP usa SQLite temporário + MockRedis para não tocar
em `lol_manager.db` nem depender de Postgres/Redis reais.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture
async def api_client(tmp_path, monkeypatch):
    """
    AsyncClient ASGI apontando para a app FastAPI com DB de teste isolado.
    """
    db_file = tmp_path / "integration.db"
    # Windows: path com barras — aiosqlite aceita ///C:/... ou relative
    db_url = f"sqlite+aiosqlite:///{db_file.as_posix()}"

    test_engine = create_async_engine(
        db_url,
        connect_args={"check_same_thread": False},
        echo=False,
    )
    TestSessionLocal = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    import src.core.database as database
    import src.main as main_mod
    import src.api.routes.seed as seed_mod
    import src.modules.simulation.match_engine_service as mes_mod

    monkeypatch.setattr(database, "engine", test_engine)
    monkeypatch.setattr(database, "AsyncSessionLocal", TestSessionLocal)
    monkeypatch.setattr(seed_mod, "engine", test_engine)
    monkeypatch.setattr(main_mod, "engine", test_engine)
    # Live match persistence usa AsyncSessionLocal global
    monkeypatch.setattr(mes_mod, "AsyncSessionLocal", TestSessionLocal, raising=False)

    async def override_get_db():
        async with TestSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    from src.core.database import get_db
    from src.main import app
    from src.core.redis_client import redis_client
    from src.models import Base

    app.dependency_overrides[get_db] = override_get_db
    # Também override se rotas capturaram get_db por referência de Depends
    app.dependency_overrides[database.get_db] = override_get_db

    # Redis mock limpo
    await redis_client.connect()
    client = redis_client._client
    if client is not None and hasattr(client, "_store"):
        client._store.clear()

    # Tabelas base (seed também recria)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    import httpx
    import inspect

    # httpx 0.27+ pode aceitar lifespan; 0.28 em alguns builds removeu o kwarg
    transport_kwargs = {"app": app}
    if "lifespan" in inspect.signature(httpx.ASGITransport.__init__).parameters:
        transport_kwargs["lifespan"] = "on"
    transport = httpx.ASGITransport(**transport_kwargs)

    # Sem lifespan automático: garante Redis mock conectado
    if redis_client._client is None:
        await redis_client.connect()

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
    await test_engine.dispose()
