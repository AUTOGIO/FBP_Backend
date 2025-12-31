"""Pydantic schemas for NFA Consult automation."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class NFAConsultRequest(BaseModel):
    """NFA consultation request model."""

    data_inicial: str = Field(
        ...,
        description="Initial date in DD/MM/YYYY format",
        example="08/12/2025",
    )
    data_final: str = Field(
        ...,
        description="Final date in DD/MM/YYYY format",
        example="10/12/2025",
    )
    matricula: Optional[str] = Field(
        default="1595504",
        description="Employee registration number (matrícula)",
        example="1595504",
    )
    username: Optional[str] = Field(
        default=None,
        description="ATF username (if not provided, uses NFA_USERNAME env var)",
    )
    password: Optional[str] = Field(
        default=None,
        description="ATF password (if not provided, uses NFA_PASSWORD env var)",
    )


class NFAConsultResponse(BaseModel):
    """NFA consultation job creation response."""

    job_id: str = Field(..., description="Job identifier")
    status: str = Field(..., description="Job status", example="queued")


class NFAJobStatusResponse(BaseModel):
    """NFA consultation job status response."""

    job_id: str = Field(..., description="Job identifier")
    job_type: str = Field(..., description="Job type", example="nfa_consult")
    status: str = Field(..., description="Job status")
    created_at: str = Field(..., description="Job creation timestamp")
    started_at: Optional[str] = Field(
        default=None,
        description="Job start timestamp",
    )
    completed_at: Optional[str] = Field(
        default=None,
        description="Job completion timestamp",
    )
    nfa_numero: Optional[str] = Field(
        default=None,
        description="NFA number found",
    )
    danfe_path: Optional[str] = Field(
        default=None,
        description="Path to downloaded DANFE PDF",
    )
    dar_path: Optional[str] = Field(
        default=None,
        description="Path to downloaded DAR PDF",
    )
    result: Optional[dict] = Field(
        default=None,
        description="Job result data (if completed)",
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message (if failed)",
    )
