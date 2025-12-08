# FBP n8n Integration Guide

This directory contains documentation for integrating FBP (FastAPI Backend) with n8n workflows.

## Overview

All FBP endpoints are designed to be n8n-compatible, returning responses in a standardized format:

```json
{
  "success": true|false,
  "data": {},
  "errors": []
}
```

## Quick Start

1. **Set Environment Variable in n8n:**
   ```env
   FBP_URL=http://localhost:8000
   ```

2. **Use HTTP Request Node:**
   - Method: POST (or GET where applicable)
   - URL: `{{ $env.FBP_URL }}/api/{module}/{endpoint}`
   - Body: JSON (as specified in each module's documentation)

3. **Handle Responses:**
   - Check `success` field
   - Access data via `data` field
   - Handle errors via `errors` array

## Available Modules

### 📧 REDESIM
- **Documentation:** [REDESIM.md](./REDESIM.md)
- **Endpoints:**
  - `POST /api/redesim/extract` - Extract REDESIM data
  - `POST /api/redesim/email/create-draft` - Create Gmail draft
  - `POST /api/redesim/email/send` - Send email from draft

### 📄 NFA
- **Documentation:** [NFA.md](./NFA.md)
- **Endpoints:**
  - `POST /api/nfa/create` - Create NFA (Nota Fiscal Avulsa)

### 🛠️ Utils
- **Documentation:** [UTILS.md](./UTILS.md)
- **Endpoints:**
  - `POST /api/utils/cep` - Validate CEP
  - `POST /api/utils/cep/batch` - Batch CEP validation

### 🌐 Browser
- **Documentation:** [BROWSER.md](./BROWSER.md)
- **Endpoints:**
  - `POST /api/browser/html` - Capture HTML from URL

## Response Format

All endpoints return responses in this format:

### Success Response
```json
{
  "success": true,
  "data": {
    // Endpoint-specific data
  },
  "errors": []
}
```

### Error Response
```json
{
  "success": false,
  "data": {},
  "errors": [
    "Error message 1",
    "Error message 2"
  ]
}
```

## Error Handling in n8n

Use n8n's error handling nodes to process errors:

1. **Check Success:**
   ```javascript
   if ($json.success === false) {
     // Handle errors
     return $json.errors;
   }
   ```

2. **Access Data:**
   ```javascript
   return $json.data;
   ```

## Security

- All endpoints use structured logging (no credential leaks)
- Gmail OAuth tokens stored in `config/auth/` (not exposed via API)
- No hard-coded credentials in responses
- Environment variables for sensitive configuration

## Testing

Run tests with:
```bash
pytest tests/n8n/
```

## Support

For issues or questions, refer to individual module documentation or check the main FBP README.

