"""
Ponto de Entrada Principal (FastAPI) para o LoL Manager Backend.

Inicializa as conexões com o PostgreSQL (SQLAlchemy) e Redis.
Rotas HTTP vivem em src/api/routes/* e são registradas via include_routers.
"""

import logging

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

app = FastAPI(
    title="League of Legends Manager Backend",
    description="Engine e Simulador de Gestão de Esports de alta performance matemática.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em prod, limitar para a URL do frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Lifespan Events ---
@app.on_event("startup")
async def startup_event():
    logger.info("Iniciando conexões do sistema...")
    await redis_client.connect()
    logger.info("Redis conectado com sucesso.")

    # Auto-criação de tabelas no banco de dados SQLite (Zero Dependency Mode)
    if settings.database_url.startswith("sqlite"):
        logger.info("Iniciando auto-criação de tabelas no SQLite local...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Tabelas SQLite auto-criadas com sucesso.")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Fechando conexões do sistema...")
    await redis_client.disconnect()
    logger.info("Redis desconectado.")


# --- Routers modulares ---
include_routers(app)
