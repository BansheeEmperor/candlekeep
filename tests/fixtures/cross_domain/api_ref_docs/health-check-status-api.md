---
title: Health Check Status API
description: API for retrieving the current health status of a system
keywords: [health, status, monitoring, system, api]
category: api-reference
---

## GET /health

Retrieves the current health status of the system.

### Parameters
None

### Response
```json
{
  "status": "ok",
  "services": [
    {
      "name": "database",
      "status": "ok"
    },
    {
      "name": "cache",
      "status": "ok"
    },
    {
      "name": "message-queue",
      "status": "degraded"
    }
  ]
}
```

### Error Codes
- `500 Internal Server Error`: An unexpected error occurred while processing the request.

## GET /health/{service}

Retrieves the health status of a specific service.

### Parameters
| Name | Type | Description |
| --- | --- | --- |
| `service` | `string` | The name of the service to check. |

### Response
```json
{
  "status": "ok",
  "service": {
    "name": "database",
    "status": "ok",
    "details": {
      "version": "10.5.0",
      "uptime": "12h 34m 56s",
      "connections": 123
    }
  }
}
```

### Error Codes
- `404 Not Found`: The requested service was not found.
- `500 Internal Server Error`: An unexpected error occurred while processing the request.

## POST /health/check

Manually triggers a health check for the system.

### Request Body
```json
{
  "services": ["database", "cache", "message-queue"]
}
```

### Response
```json
{
  "status": "ok",
  "services": [
    {
      "name": "database",
      "status": "ok"
    },
    {
      "name": "cache",
      "status": "ok"
    },
    {
      "name": "message-queue",
      "status": "degraded"
    }
  ]
}
```

### Error Codes
- `400 Bad Request`: The request body is invalid or missing required parameters.
- `500 Internal Server Error`: An unexpected error occurred while processing the request.

## GET /health/history

Retrieves the health status history for the system.

### Parameters
| Name | Type | Description |
| --- | --- | --- |
| `limit` | `integer` | The maximum number of records to return. |
| `offset` | `integer` | The number of records to skip. |

### Response
```json
{
  "status": "ok",
  "history": [
    {
      "timestamp": "2023-04-01T12:00:00Z",
      "services": [
        {
          "name": "database",
          "status": "ok"
        },
        {
          "name": "cache",
          "status": "ok"
        },
        {
          "name": "message-queue",
          "status": "ok"
        }
      ]
    },
    {
      "timestamp": "2023-04-01T12:10:00Z",
      "services": [
        {
          "name": "database",
          "status": "ok"
        },
        {
          "name": "cache",
          "status": "ok"
        },
        {
          "name": "message-queue",
          "status": "degraded"
        }
      ]
    }
  ]
}
```

### Error Codes
- `400 Bad Request`: The request parameters are invalid.
- `500 Internal Server Error`: An unexpected error occurred while processing the request.