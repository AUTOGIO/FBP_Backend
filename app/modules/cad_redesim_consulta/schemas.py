"""Schemas for CAD REDESIM consulta automation."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

DEFAULT_INICIO = "10/12/2025"
DEFAULT_FIM = "17/12/2025"


class CadRedesimConsultaRequest(BaseModel):
    """Request payload for REDESIM consulta automation."""

    data_criacao_inicio: Optional[str] = Field(
        default=None,
        description="Data inicial (DD/MM/AAAA); se omitida, usa default diário.",
    )
    data_criacao_fim: Optional[str] = Field(
        default=None,
        description="Data final (DD/MM/AAAA); se omitida, usa default diário.",
    )
    wait_user_dates: bool = Field(
        default=True,
        description="Se True, aguarda usuário confirmar datas no UI antes de consultar.",
    )
    username: Optional[str] = Field(
        default=None, description="Usuário ATF (fallback para env)."
    )
    password: Optional[str] = Field(
        default=None, description="Senha ATF (fallback para env)."
    )


class CadRedesimConsultaResponse(BaseModel):
    job_id: str = Field(..., description="Identificador do job.")
    status: str = Field(..., description="queued|running|completed|failed")
    execution_id: Optional[str] = Field(
        default=None, description="Identificador da execução."
    )


class CadRedesimJobStatusResponse(BaseModel):
    job_id: str
    status: str
    result: Optional[dict] = None
    error: Optional[str] = None
