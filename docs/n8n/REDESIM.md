# REDESIM n8n Integration Guide

This document describes how to use FBP REDESIM endpoints with n8n HTTP Request nodes.

## Base URL

```
http://localhost:8000/api/redesim
```

## Endpoints

### 1. Extract REDESIM Data

**Endpoint:** `POST /extract`

**Description:** Extract REDESIM process data using browser automation.

**Request Body:**
```json
{
  "url": "https://atf.sefaz.pb.gov.br/",
  "config": {
    "browser": {
      "headless": true
    }
  }
}
```

**Response Format (n8n-friendly):**
```json
{
  "success": true,
  "data": {
    "job_id": "traces/atf_redesim_20250101_120000.csv",
    "processes_found": 15,
    "report_path": "traces/atf_redesim_20250101_120000.csv",
    "results": [
      {
        "processo": "2344402025-2",
        "razao_social": "REINO DO SORVETE COMERCIO DE ALIMENTOS LTDA",
        "emails": ["email@example.com"]
      }
    ]
  },
  "errors": []
}
```

**n8n Configuration:**
- **Method:** POST
- **URL:** `{{ $env.FBP_URL }}/api/redesim/extract`
- **Body:** JSON (use above format)
- **Response Format:** JSON

**Error Handling:**
```json
{
  "success": false,
  "data": {},
  "errors": ["Error message here"]
}
```

---

### 2. Create Gmail Draft

**Endpoint:** `POST /email/create-draft`

**Description:** Create a Gmail draft email.

**Request Body:**
```json
{
  "to": "recipient@example.com",
  "subject": "Processo: 2344402025-2 - Razão Social: COMPANY NAME",
  "body": "Email body text here...",
  "attachments": ["/path/to/file.pdf"]
}
```

**Response Format:**
```json
{
  "success": true,
  "data": {
    "draft_id": "r1234567890",
    "message_id": "msg1234567890",
    "thread_id": "thread1234567890"
  },
  "errors": []
}
```

**n8n Configuration:**
- **Method:** POST
- **URL:** `{{ $env.FBP_URL }}/api/redesim/email/create-draft`
- **Body:** JSON
- **Authentication:** Not required (uses OAuth tokens from config/auth/)

**Note:** Gmail credentials must be configured in `config/auth/credentials.json` and `config/auth/token.json`.

---

### 3. Send Email from Draft

**Endpoint:** `POST /email/send`

**Description:** Send an email from a Gmail draft.

**Request Body:**
```json
{
  "draft_id": "r1234567890"
}
```

**Response Format:**
```json
{
  "success": true,
  "data": {
    "draft_id": "r1234567890",
    "sent": true
  },
  "errors": []
}
```

**n8n Configuration:**
- **Method:** POST
- **URL:** `{{ $env.FBP_URL }}/api/redesim/email/send`
- **Body:** JSON

---

## n8n Workflow Examples

### Example 1: Extract and Create Draft

```json
{
  "nodes": [
    {
      "name": "Extract REDESIM",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "method": "POST",
        "url": "http://localhost:8000/api/redesim/extract",
        "body": {
          "url": "https://atf.sefaz.pb.gov.br/"
        }
      }
    },
    {
      "name": "Create Draft",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "method": "POST",
        "url": "http://localhost:8000/api/redesim/email/create-draft",
        "body": {
          "to": "{{ $json.data.results[0].emails[0] }}",
          "subject": "Processo: {{ $json.data.results[0].processo }}",
          "body": "Email body..."
        }
      }
    }
  ]
}
```

---

## Environment Variables

Set these in n8n environment:

```env
FBP_URL=http://localhost:8000
```

---

## Error Handling

All endpoints return errors in the `errors` array:

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

Use n8n's error handling nodes to process these errors.

---

## Security Notes

- Gmail OAuth tokens are stored in `config/auth/token.json` (not exposed via API)
- Never commit `token.json` or `credentials.json` to version control
- Use environment variables for sensitive configuration
- All endpoints use structured logging (no credential leaks)

