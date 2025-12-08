# Utils n8n Integration Guide

This document describes how to use FBP utility endpoints with n8n HTTP Request nodes.

## Base URL

```
http://localhost:8000/api/utils
```

## Endpoints

### 1. Validate CEP

**Endpoint:** `POST /cep`

**Description:** Validate Brazilian postal code (CEP) and optionally enrich with additional data.

**Request Body:**
```json
{
  "cep": "05424020",
  "enrich": true
}
```

**Response Format (n8n-friendly):**
```json
{
  "success": true,
  "data": {
    "cep": "05424020",
    "valid": true,
    "logradouro": "Rua Exemplo",
    "bairro": "Bairro Exemplo",
    "cidade": "São Paulo",
    "uf": "SP",
    "ibge": "3550308",
    "source": "viacep",
    "coordinates": {
      "latitude": -23.5505,
      "longitude": -46.6333
    }
  },
  "errors": []
}
```

**n8n Configuration:**
- **Method:** POST
- **URL:** `{{ $env.FBP_URL }}/api/utils/cep`
- **Body:** JSON

**Error Response:**
```json
{
  "success": false,
  "data": {
    "cep": "12345678",
    "valid": false
  },
  "errors": ["Invalid CEP format"]
}
```

---

### 2. Batch CEP Validation

**Endpoint:** `POST /cep/batch`

**Description:** Validate multiple CEPs in a single request.

**Request Body:**
```json
{
  "ceps": ["05424020", "01310100", "20040020"]
}
```

**Response Format:**
```json
{
  "success": true,
  "data": {
    "total": 3,
    "validated": {
      "05424020": {
        "valid": true,
        "logradouro": "Rua Exemplo",
        "cidade": "São Paulo",
        "uf": "SP"
      },
      "01310100": {
        "valid": true,
        "logradouro": "Avenida Exemplo",
        "cidade": "São Paulo",
        "uf": "SP"
      },
      "20040020": {
        "valid": false,
        "error": "CEP not found"
      }
    },
    "valid_count": 2,
    "invalid_count": 1
  },
  "errors": []
}
```

**n8n Configuration:**
- **Method:** POST
- **URL:** `{{ $env.FBP_URL }}/api/utils/cep/batch`
- **Body:** JSON

---

## n8n Workflow Examples

### Example: Validate CEP and Enrich Company Data

```json
{
  "nodes": [
    {
      "name": "Validate CEP",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "method": "POST",
        "url": "http://localhost:8000/api/utils/cep",
        "body": {
          "cep": "{{ $json.company.cep }}",
          "enrich": true
        }
      }
    },
    {
      "name": "Merge Data",
      "type": "n8n-nodes-base.merge",
      "parameters": {
        "mode": "combine",
        "combineBy": "all"
      }
    }
  ]
}
```

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

## Performance Notes

- CEP validation uses caching (24-hour TTL by default)
- Batch validation processes CEPs sequentially with small delays
- API fallback system ensures high reliability

