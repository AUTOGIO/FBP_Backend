"""Echo router."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.services import echo_service

router = APIRouter(prefix="/echo", tags=["echo"])


class EchoRequest(BaseModel):
    """Echo request model."""

    message: str


class EchoResponse(BaseModel):
    """Echo response model."""

    echo: str


@router.post("")
async def echo(request: EchoRequest) -> EchoResponse:
    """Echo endpoint - returns the input message.

    Args:
        request: Echo request with message

    Returns:
        Echoed message

    """
    result = await echo_service.echo_message(request.message)
    return EchoResponse(**result)
