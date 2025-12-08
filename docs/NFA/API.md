# NFA API Documentation

## Endpoints

### POST /api/nfa/create

Create a single NFA (Nota Fiscal Avulsa).

**Request Body:**
```json
{
  "emitente": {
    "cnpj": "12345678000190"
  },
  "destinatario": {
    "documento": "12345678900",
    "endereco": {
      "cep": "58000000",
      "logradouro": "Rua Exemplo",
      "numero": "123",
      "complemento": "",
      "bairro": "Centro",
      "uf": "PB"
    }
  },
  "produtos": [
    {
      "descricao": "Produto Exemplo",
      "unidade": "un",
      "valor": "100.00",
      "quantidade": "1",
      "aliquota": "0.00"
    }
  ],
  "config": {
    "browser": {
      "headless": false
    }
  }
}
```

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "nfa_id": "123456789",
    "status": "created"
  },
  "errors": []
}
```

**Response (Error):**
```json
{
  "success": false,
  "data": {},
  "errors": ["Error message here"]
}
```

## n8n Integration

Use HTTP Request node in n8n:

- **Method**: POST
- **URL**: `{{ $env.FBP_URL }}/api/nfa/create`
- **Body**: JSON (as above)

## Error Codes

- **400**: Invalid request data
- **422**: Validation error
- **500**: Server error

## Rate Limiting

- No rate limiting currently implemented
- Recommended: 1 request per 5 seconds for batch operations

