"""n8n-compatible NFA endpoints.
All responses follow n8n-friendly format: {success, data, errors}.
"""

import logging
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.nfa_service import create_nfa, create_nfa_batch

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/nfa", tags=["n8n", "nfa"])


class N8NResponse(BaseModel):
    """Standard n8n response format."""

    success: bool
    data: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)


class CreateNFARequest(BaseModel):
    """NFA creation request."""

    emitente: dict[str, Any] = Field(..., description="Emitente data")
    destinatario: dict[str, Any] = Field(..., description="Destinatario data")
    produtos: list[dict[str, Any]] = Field(..., description="Product list")
    natureza_operacao: str | None = Field(None, description="Natureza da operação")
    motivo: str | None = Field(None, description="Motivo")
    reparticao_fiscal: str | None = Field(None, description="Repartição fiscal")
    codigo_municipio: str | None = Field(None, description="Código do município")
    tipo_operacao: str | None = Field(None, description="Tipo de operação")
    cfop: str | None = Field(None, description="CFOP")
    informacoes_adicionais: str | None = Field(
        None,
        description="Informações adicionais",
    )
    credentials: dict[str, str] | None = Field(
        None,
        description="Optional login credentials",
    )
    config: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional configuration",
    )


class BatchNFARequest(BaseModel):
    """Batch NFA creation request."""

    emitente_cnpj: str = Field(..., description="Emitente CNPJ")
    destinatarios: list[str] = Field(..., description="List of CPFs")
    config: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional configuration",
    )
    credentials: dict[str, str] | None = Field(
        None,
        description="Optional login credentials",
    )


@router.post("/create")
async def create_nfa_endpoint(request: CreateNFARequest) -> N8NResponse:
    """Create NFA (Nota Fiscal Avulsa).

    n8n-compatible endpoint for NFA creation.
    """
    errors: list[str] = []
    data: dict[str, Any] = {}

    try:
        # Prepare form data from request

        # Map to internal format - preserve all fields
        mapped_data = {
            "emitente": request.emitente,
            "destinatario": request.destinatario,
            "produtos": request.produtos,
            "natureza_operacao": request.natureza_operacao,
            "motivo": request.motivo,
            "reparticao_fiscal": request.reparticao_fiscal,
            "codigo_municipio": request.codigo_municipio,
            "tipo_operacao": request.tipo_operacao,
            "cfop": request.cfop,
            # Legacy format support
            "emitente_cnpj": request.emitente.get("cnpj", ""),
            "destinatario_doc": request.destinatario.get("documento", ""),
            "endereco": request.destinatario.get("endereco", {}),
            "item": request.produtos[0] if request.produtos else {},
            "informacoes_adicionais": request.informacoes_adicionais,
        }

        # Call service with credentials if provided
        result = await create_nfa(
            mapped_data,
            config=request.config,
            credentials=request.credentials,
        )

        if result["success"]:
            data = result["data"]
            return N8NResponse(success=True, data=data, errors=[])
        errors = result.get("errors", ["Unknown error"])
        return N8NResponse(success=False, data=data, errors=errors)

    except Exception as e:
        logger.error(f"Error in NFA creation: {e}", exc_info=True)
        errors.append(str(e))
        return N8NResponse(success=False, data=data, errors=errors)


@router.post("/batch")
async def create_nfa_batch_endpoint(request: BatchNFARequest) -> N8NResponse:
    """Create multiple NFAs in batch.

    n8n-compatible endpoint for batch NFA creation.
    Only requires emitente_cnpj and list of destinatario CPFs.
    All other fields are filled automatically with fixed values.
    """
    errors: list[str] = []
    data: dict[str, Any] = {}

    try:
        # Build form_data_list from simplified request
        form_data_list = []

        for cpf in request.destinatarios:
            # Use fixed values for all fields except CPF
            form_data = {
                "emitente": {
                    "cnpj": request.emitente_cnpj,
                },
                "destinatario": {
                    "cpf": cpf,
                    "documento": cpf,  # Support both field names
                },
                "natureza_operacao": "REMESSA",
                "motivo": "DESPACHO",
                "reparticao_fiscal": "90102008",
                "codigo_municipio": "2051-6",
                "tipo_operacao": "SAIDA",
                "cfop": "6908",
                "produtos": [
                    {
                        "ncm": "0000.00.00",
                        "descricao": "1 - SID241",
                        "detalhamento_produto": "1 - SID241",
                        "unidade": "UN",
                        "quantidade": 1,
                        "valor_unitario": 1100,
                        "aliquota": 0,
                        "cst": "41",
                        "receita": "1199 - ICMS - OUTROS (COMERCIO E INDUSTRIA)",
                    },
                ],
                "informacoes_adicionais": "Remessa por conta de contrato de locacao",
            }
            form_data_list.append(form_data)

        # Call batch service
        result = await create_nfa_batch(
            form_data_list,
            config=request.config,
            credentials=request.credentials,
        )

        if result["success"]:
            # Format response with summary
            batch_data = result["data"]
            summary = batch_data.get("batch_summary", {})
            results = batch_data.get("results", [])

            # Format results for response
            formatted_results = []
            for r in results:
                formatted_results.append(
                    {
                        "cpf": r.get("cpf"),
                        "status": r.get("status"),
                        "nfa_number": r.get("nfa_number"),
                        "dar_pdf": r.get("dar_pdf"),
                        "nota_pdf": r.get("nota_pdf"),
                        "error": r.get("error"),
                    }
                )

            data = {
                "generated": summary.get("success_count", 0),
                "total": summary.get("total_processed", 0),
                "success_count": summary.get("success_count", 0),
                "failure_count": summary.get("failure_count", 0),
                "results": formatted_results,
            }
            return N8NResponse(success=True, data=data, errors=[])

        errors = result.get("errors", ["Unknown error"])
        return N8NResponse(success=False, data=data, errors=errors)

    except Exception as e:
        logger.error(f"Error in batch NFA creation: {e}", exc_info=True)
        errors.append(str(e))
        return N8NResponse(success=False, data=data, errors=errors)
