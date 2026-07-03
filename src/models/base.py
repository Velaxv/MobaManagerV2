"""
Classe base e mixins para os modelos SQLAlchemy do LoL Manager.
Todos os modelos herdam de Base, e podem opcionalmente usar UUIDMixin e TimestampMixin.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Classe base para todos os modelos SQLAlchemy do LoL Manager."""
    pass


class TimestampMixin:
    """
    Mixin que adiciona campos de auditoria de criação e atualização.
    Os valores são definidos automaticamente pelo banco de dados.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Data e hora de criação do registro (fuso horário UTC).",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        doc="Data e hora da última atualização do registro (fuso horário UTC).",
    )


class UUIDMixin:
    """
    Mixin que adiciona campo de ID UUID como chave primária.
    O UUID é gerado automaticamente pela aplicação (não pelo banco),
    garantindo previsibilidade e portabilidade entre bancos de dados.
    """

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
        doc="Identificador único do registro (UUID v4).",
    )
