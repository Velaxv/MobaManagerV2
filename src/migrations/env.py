"""
Configuração do ambiente Alembic para suporte a migrações assíncronas.

Utiliza o async engine do SQLAlchemy para conectar ao PostgreSQL.
A URL do banco é lida da variável de ambiente SYNC_DATABASE_URL.
"""
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context
import os
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Importa todos os models para que o Alembic detecte as tabelas automaticamente
from src.models import Base  # noqa: F401
from src.models.player import Player  # noqa: F401
from src.models.team import Team  # noqa: F401
from src.models.contract import Contract  # noqa: F401
from src.models.league import League, LeagueTeam  # noqa: F401
from src.models.match import Match  # noqa: F401

# Objeto de configuração do Alembic (lê o alembic.ini)
config = context.config

# Sobrescreve a URL do banco com a variável de ambiente (formato síncrono para Alembic)
config.set_main_option("sqlalchemy.url", os.environ["SYNC_DATABASE_URL"])

# Configura o logging via arquivo .ini, se disponível
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Referência para os metadados dos models — usado pelo Alembic para gerar migrações
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Executa migrações em modo offline (sem conexão ao banco).
    Gera SQL puro que pode ser revisado antes de aplicar.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """
    Executa as migrações em uma conexão síncrona (chamado via run_sync).
    """
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    Configura e executa migrações com o async engine do SQLAlchemy.
    Usa NullPool para evitar conexões ociosas durante migrações.
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        # run_sync permite executar código síncrono dentro de um contexto assíncrono
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """
    Ponto de entrada para migrações online (com conexão ao banco ativa).
    Usa asyncio.run para executar o coroutine assíncrono.
    """
    asyncio.run(run_async_migrations())


# Seleciona o modo de execução baseado no contexto do Alembic
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
