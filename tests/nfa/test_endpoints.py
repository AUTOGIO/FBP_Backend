"""Tests for NFA endpoints."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_create_nfa_endpoint_structure() -> None:
    """Test that create NFA endpoint returns n8n-friendly format."""
    response = client.post(
        "/api/nfa/create",
        json={
            "emitente": {"cnpj": "12345678000190"},
            "destinatario": {
                "documento": "12345678900",
                "endereco": {
                    "cep": "58000000",
                    "logradouro": "Rua Teste",
                    "numero": "123",
                    "bairro": "Centro",
                    "uf": "PB",
                },
            },
            "produtos": [
                {
                    "descricao": "Produto Teste",
                    "unidade": "un",
                    "valor": "100.00",
                    "quantidade": "1",
                    "aliquota": "0.00",
                },
            ],
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Check n8n-friendly structure
    assert "success" in data
    assert "data" in data
    assert "errors" in data
    assert isinstance(data["success"], bool)
    assert isinstance(data["data"], dict)
    assert isinstance(data["errors"], list)
