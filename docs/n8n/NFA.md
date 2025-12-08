# NFA n8n Integration Guide

This document describes how to use FBP NFA endpoints with n8n HTTP Request nodes.

## Base URL

```
http://localhost:8000/api/nfa
```

## Endpoints

### 1. Create NFA

**Endpoint:** `POST /create`

**Description:** Create NFA (Nota Fiscal Avulsa) using ATF automation.

**Request Body:**
```json
{
  "emitente": {
    "cnpj": "12.345.678/0001-90",
    "razao_social": "EMPRESA EXEMPLO LTDA",
    "inscricao_estadual": "123456789"
  },
  "destinatario": {
    "cpf_cnpj": "123.456.789-00",
    "nome": "CLIENTE EXEMPLO",
    "endereco": "Rua Exemplo, 123"
  },
  "produtos": [
    {
      "codigo": "123456",
      "descricao": "Produto Exemplo",
      "quantidade": 1,
      "valor_unitario": 100.00
    }
  ],
  "config": {
    "headless": true
  }
}
```

**Response Format (n8n-friendly):**
```json
{
  "success": true,
  "data": {
    "nfa_id": "123456789",
    "status": "created",
    "processo": "2344402025-2"
  },
  "errors": []
}
```

**n8n Configuration:**
- **Method:** POST
- **URL:** `{{ $env.FBP_URL }}/api/nfa/create`
- **Body:** JSON

**Note:** This endpoint is currently a placeholder. NFA modules migration is pending.

---

## Error Handling

All endpoints return errors in the `errors` array:

```json
{
  "success": false,
  "data": {},
  "errors": [
    "Error message here"
  ]
}
```

---

## Security Notes

- ATF credentials should be configured via environment variables
- No hard-coded credentials in API responses
- All operations use structured logging

