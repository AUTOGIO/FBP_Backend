# Browser n8n Integration Guide

This document describes how to use FBP browser automation endpoints with n8n HTTP Request nodes.

## Base URL

```
http://localhost:8000/api/browser
```

## Endpoints

### 1. Capture HTML

**Endpoint:** `POST /html`

**Description:** Capture HTML content from a URL using browser automation (Cursor Browser Agent or Playwright fallback).

**Request Body:**
```json
{
  "url": "https://atf.sefaz.pb.gov.br/",
  "use_cursor": true,
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
    "url": "https://atf.sefaz.pb.gov.br/",
    "html_length": 125430,
    "html": "<html>...first 10KB...</html>",
    "truncated": true
  },
  "errors": []
}
```

**n8n Configuration:**
- **Method:** POST
- **URL:** `{{ $env.FBP_URL }}/api/browser/html`
- **Body:** JSON

**Parameters:**
- `url` (required): URL to capture HTML from
- `use_cursor` (optional, default: true): Try Cursor browser first, fallback to Playwright
- `config` (optional): Browser configuration dictionary

**Note:** HTML response is truncated to first 10KB. Use the `html_length` field to check if truncation occurred.

---

## n8n Workflow Examples

### Example: Capture HTML and Extract Data

```json
{
  "nodes": [
    {
      "name": "Capture HTML",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "method": "POST",
        "url": "http://localhost:8000/api/browser/html",
        "body": {
          "url": "https://atf.sefaz.pb.gov.br/",
          "use_cursor": true
        }
      }
    },
    {
      "name": "Extract Data",
      "type": "n8n-nodes-base.code",
      "parameters": {
        "jsCode": "// Process HTML from previous node\nconst html = $input.item.json.data.html;\n// Your extraction logic here\nreturn { extracted: 'data' };"
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

**Common Errors:**
- `"Cursor Browser API not available"` - Cursor browser not available, will fallback to Playwright
- `"Playwright not available"` - Playwright not installed
- `"Failed to extract HTML with Playwright: ..."` - Playwright extraction failed

---

## Browser Configuration

The `config` parameter accepts:

```json
{
  "browser": {
    "headless": true,
    "timeout": 30000
  },
  "runtime": {
    "base_url": "https://atf.sefaz.pb.gov.br/"
  }
}
```

---

## Security Notes

- Browser automation runs in isolated context
- No credentials exposed in HTML responses
- All operations use structured logging
- Playwright runs in headless mode by default

