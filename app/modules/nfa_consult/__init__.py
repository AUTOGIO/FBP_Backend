"""NFA Consult Automation Module.

This module provides automation for consulting and downloading NFAs
(DANFE + DAR) from the ATF/SEFAZ-PB portal using Playwright.
"""

from app.modules.nfa_consult.router import router
from app.modules.nfa_consult.schemas import (
    NFAConsultRequest,
    NFAConsultResponse,
    NFAJobStatusResponse,
)
from app.modules.nfa_consult.services import (
    create_nfa_consult_job,
    get_nfa_consult_job_status,
)
from app.modules.nfa_consult.tasks import run_nfa_consult_automation

__all__ = [
    "router",
    "NFAConsultRequest",
    "NFAConsultResponse",
    "NFAJobStatusResponse",
    "create_nfa_consult_job",
    "get_nfa_consult_job_status",
    "run_nfa_consult_automation",
]
