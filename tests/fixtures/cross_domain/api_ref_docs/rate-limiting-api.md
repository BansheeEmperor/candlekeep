---
title: Rate Limiting API
description: API for managing rate limiting rules and monitoring usage
keywords: [rate limiting, API throttling, usage monitoring, access control]
category: api-reference
---

## GET /api/v1/rate-limits
Retrieve a list of all rate limiting rules.

### Parameters
| Name | Type | Description |
| --- | --- | --- |
| `page` | `integer` | Page number for pagination (default: 1) |
| `limit` | `integer` | Number of results per page (default: 20, max: 100) |

### Response
```json
{
  "data": [
    {
      "id": "abc123",
      "name": "API Request Limit",
      "description": "Limit API requests per minute",
      "resource": "/api/*",
      "limit": 100,
      "interval": 60,
      "enabled": true
    },
    {
      "id": "def456",
      "name": "Login Attempts",
      "description": "Limit login attempts per IP address",
      "resource": "/login",
      "limit": 5,
      "interval": 300,
      "enabled": true
    }
  ],
  "meta": {
    "total": 2,
    "page": 1,
    "limit": 20
  }
}
```

## POST /api/v1/rate-limits
Create a new rate limiting rule.

### Request Body
```json
{
  "name": "API Request Limit",
  "description": "Limit API requests per minute",
  "resource": "/api/*",
  "limit": 100,
  "interval": 60,
  "enabled": true
}
```

### Response
```json
{
  "id": "abc123",
  "name": "API Request Limit",
  "description": "Limit API requests per minute",
  "resource": "/api/*",
  "limit": 100,
  "interval": 60,
  "enabled": true
}
```

## GET /api/v1/rate-limits/{id}
Retrieve a specific rate limiting rule.

### Parameters
| Name | Type | Description |
| --- | --- | --- |
| `id` | `string` | ID of the rate limiting rule |

### Response
```json
{
  "id": "abc123",
  "name": "API Request Limit",
  "description": "Limit API requests per minute",
  "resource": "/api/*",
  "limit": 100,
  "interval": 60,
  "enabled": true
}
```

## PUT /api/v1/rate-limits/{id}
Update an existing rate limiting rule.

### Parameters
| Name | Type | Description |
| --- | --- | --- |
| `id` | `string` | ID of the rate limiting rule |

### Request Body
```json
{
  "name": "API Request Limit",
  "description": "Limit API requests per minute",
  "resource": "/api/*",
  "limit": 200,
  "interval": 60,
  "enabled": true
}
```

### Response
```json
{
  "id": "abc123",
  "name": "API Request Limit",
  "description": "Limit API requests per minute",
  "resource": "/api/*",
  "limit": 200,
  "interval": 60,
  "enabled": true
}
```

## GET /api/v1/usage
Retrieve usage statistics for the current user or organization.

### Parameters
| Name | Type | Description |
| --- | --- | --- |
| `start_date` | `date` | Start date for the usage report |
| `end_date` | `date` | End date for the usage report |
| `resource` | `string` | Filter usage by a specific resource |

### Response
```json
{
  "data": [
    {
      "resource": "/api/*",
      "limit": 100,
      "interval": 60,
      "total_requests": 5000,
      "remaining_requests": 50,
      "reset_time": "2023-04-01T00:00:00Z"
    },
    {
      "resource": "/login",
      "limit": 5,
      "interval": 300,
      "total_requests": 10,
      "remaining_requests": 0,
      "reset_time": "2023-04-01T00:05:00Z"
    }
  ]
}
```

### Error Codes
| Status Code | Description |
| --- | --- |
| 400 | Bad Request (e.g., invalid parameters) |
| 401 | Unauthorized (invalid or missing API key) |
| 403 | Forbidden (user not allowed to access the requested resource) |
| 404 | Not Found (the requested resource does not exist) |
| 429 | Too Many Requests (rate limit exceeded) |
| 500 | Internal Server Error |