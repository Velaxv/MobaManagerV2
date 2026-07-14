"""
Ponto de Entrada Principal (FastAPI) para o LoL Manager Backend.

Inicializa as conexões com o PostgreSQL (SQLAlchemy) e Redis.
Rotas HTTP vivem em src/api/routes/* e são registradas via include_routers.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import get_settings
from src.core.database import engine
from src.core.redis_client import redis_client
from src.models import Base
from src.api.routes import include_routers

# Configuração de Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("lol_manager_api")
settings = get_settings()


async def _sqlite_bootstrap() -> None:
    """Auto-cria tabelas e aplica migrações leves no SQLite local."""
    if not settings.database_url.startswith("sqlite"):
        return
    logger.info("Iniciando auto-criação de tabelas no SQLite local...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        def _sqlite_light_migrate(sync_conn):
            from sqlalchemy import text

            cols = {
                row[1]
                for row in sync_conn.execute(text("PRAGMA table_info(players)")).fetchall()
            }
            if "is_starter" not in cols:
                sync_conn.execute(
                    text(
                        "ALTER TABLE players ADD COLUMN is_starter BOOLEAN "
                        "NOT NULL DEFAULT 0"
                    )
                )
                logger.info("SQLite: coluna players.is_starter adicionada.")

        await conn.run_sync(_sqlite_light_migrate)
    logger.info("Tabelas SQLite auto-criadas com sucesso.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown (substitui on_event deprecado)."""
    logger.info("Iniciando conexões do sistema...")
    await redis_client.connect()
    logger.info("Redis conectado com sucesso.")
    await _sqlite_bootstrap()
    yield
    logger.info("Fechando conexões do sistema...")
    await redis_client.disconnect()
    logger.info("Redis desconectado.")


app = FastAPI(
    title="League of Legends Manager Backend",
    description="Engine e Simulador de Gestão de Esports de alta performance matemática.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em prod, limitar para a URL do frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routers modulares ---
include_routers(app)
