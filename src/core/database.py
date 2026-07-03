# Motor de banco de dados assíncrono compatível com PostgreSQL e SQLite
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import event
from src.core.config import get_settings
import os

settings = get_settings()

# Configurações adicionais para compatibilidade com SQLite
connect_args = {}
if settings.database_url.startswith("sqlite"):
    # Permite acesso ao SQLite em múltiplos threads no FastAPI
    connect_args = {"check_same_thread": False}

# Engine com pool configurado
engine = create_async_engine(
    settings.database_url,
    connect_args=connect_args,
    pool_pre_ping=True,
    echo=settings.debug,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Registra trigger para chaves estrangeiras no SQLite
if settings.database_url.startswith("sqlite"):
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

class Base(DeclarativeBase):
    pass

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
