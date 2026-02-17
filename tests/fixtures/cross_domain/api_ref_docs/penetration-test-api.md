---
title: Penetration Test API
description: A RESTful API for conducting penetration tests on web applications.
keywords:
  - penetration testing
  - web security
  - vulnerability assessment
  - api
  - cybersecurity
category: api-reference
---

## GET /api/v1/websites

Retrieves a list of websites that are available for penetration testing.

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `page` | integer | No | The page number to retrieve (default: 1) |
| `limit` | integer | No | The number of results to return per page (default: 20) |

### Response

```json
{
  "data": [
    {
      "id": "1",
      "name": "Example Website",
      "url": "https://example.com",
      "status": "active"
    },
    {
      "id": "2",
      "name": "Test Application",
      "url": "https://test.example.com",
      "status": "active"
    }
  ],
  "meta": {
    "total": 2,
    "page": 1,
    "limit": 20
  }
}
```

### Error Codes

| Status Code | Description |
| --- | --- |
| 400 | Bad Request - Invalid parameters |
| 500 | Internal Server Error - Failed to retrieve websites |

## POST /api/v1/websites/{id}/tests

Initiates a new penetration test on the specified website.

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | string | Yes | The ID of the website to test |

### Request Body

```json
{
  "test_type": "full_scan",
  "scope": [
    "https://example.com",
    "https://example.com/api"
  ],
  "options": {
    "depth": 3,
    "include_subdomains": true,
    "use_headless_browser": true
  }
}
```

### Response

```json
{
  "id": "123456789",
  "website_id": "1",
  "status": "in_progress",
  "started_at": "2023-04-24T12:34:56Z",
  "estimated_completion": "2023-04-24T14:34:56Z"
}
```

### Error Codes

| Status Code | Description |
| --- | --- |
| 400 | Bad Request - Invalid request body |
| 404 | Not Found - Website not found |
| 500 | Internal Server Error - Failed to initiate test |

## GET /api/v1/websites/{id}/tests/{test_id}

Retrieves the status and details of a specific penetration test.

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | string | Yes | The ID of the website |
| `test_id` | string | Yes | The ID of the test |

### Response

```json
{
  "id": "123456789",
  "website_id": "1",
  "status": "completed",
  "started_at": "2023-04-24T12:34:56Z",
  "completed_at": "2023-04-24T14:34:56Z",
  "test_type": "full_scan",
  "scope": [
    "https://example.com",
    "https://example.com/api"
  ],
  "options": {
    "depth": 3,
    "include_subdomains": true,
    "use_headless_browser": true
  },
  "findings": [
    {
      "id": "1",
      "type": "cross-site-scripting",
      "location": "https://example.com/vulnerable-page.php",
      "severity": "high",
      "description": "Cross-site scripting vulnerability found in the user input field."
    },
    {
      "id": "2",
      "type": "sql-injection",
      "location": "https://example.com/api/users",
      "severity": "medium",
      "description": "Potential SQL injection vulnerability in the API endpoint."
    }
  ]
}
```

### Error Codes

| Status Code | Description |
| --- | --- |
| 404 | Not Found - Website or test not found |
| 500 | Internal Server Error - Failed to retrieve test details |

## DELETE /api/v1/websites/{id}/tests/{test_id}

Cancels a running penetration test.

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | string | Yes | The ID of the website |
| `test_id` | string | Yes | The ID of the test |

### Response

```json
{
  "id": "123456789",
  "status": "cancelled",
  "cancelled_at": "2023-04-24T14:00:00Z"
}
```

### Error Codes

| Status Code | Description |
| --- | --- |
| 404 | Not Found - Website or test not found |
| 409 | Conflict - Test is not in a cancelable state |
| 500 | Internal Server Error - Failed to cancel test |