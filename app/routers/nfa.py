"""NFA router."""

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.services import nfa_service

router = APIRouter(prefix="/nfa", tags=["nfa"])


class NFATestRequest(BaseModel):
    """NFA test request model (flexible for future use)."""



class NFATestResponse(BaseModel):
    """NFA test response model."""

    success: bool
    message: str


@router.post("/test")
async def test_nfa(request: NFATestRequest) -> NFATestResponse:
    """NFA test endpoint (mock implementation).

    Args:
        request: NFA test request

    Returns:
        Test response

    """
    payload: dict[str, Any] = request.model_dump()
    result = await nfa_service.test_nfa(payload)
    return NFATestResponse(**result)
