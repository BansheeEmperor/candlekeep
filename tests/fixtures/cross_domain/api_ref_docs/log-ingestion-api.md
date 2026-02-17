---
title: Log Ingestion API
description: Ingest application logs into a centralized logging system.
keywords: [logging, logs, ingestion, data, api]
category: api-reference
---

## POST /logs

Ingest a batch of application logs.

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| source | string | Yes | The source application or service name. |
| environment | string | Yes | The environment (e.g. production, staging, etc.) |
| logs | array | Yes | An array of log entries. |

### Request Body

```json
{
  "source": "my-app",
  "environment": "production",
  "logs": [
    {
      "timestamp": "2023-04-12T12:34:56.789Z",
      "level": "error",
      "message": "Database connection failed",
      "metadata": {
        "userId": "abc123",
        "requestId": "def456"
      }
    },
    {
      "timestamp": "2023-04-12T12:35:01.234Z",
      "level": "info",
      "message": "User logged in",
      "metadata": {
        "userId": "ghi789"
      }
    }
  ]
}
```

### Response

```json
{
  "success": true,
  "message": "Logs ingested successfully"
}
```

### Error Codes

| Status Code | Description |
| --- | --- |
| 400 | Bad Request - Invalid request body or parameters. |
| 401 | Unauthorized - Invalid API key or authentication. |
| 500 | Internal Server Error - An unexpected error occurred. |

## GET /logs

Retrieve a list of logs based on the specified filters.

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| source | string | No | The source application or service name. |
| environment | string | No | The environment (e.g. production, staging, etc.) |
| level | string | No | The log level (e.g. error, warn, info, debug). |
| from | string | No | The start date/time of the log entries (ISO 8601 format). |
| to | string | No | The end date/time of the log entries (ISO 8601 format). |
| limit | integer | No | The maximum number of log entries to return (default: 100, max: 1000). |
| offset | integer | No | The offset to start returning log entries from (default: 0). |

### Response

```json
{
  "total": 25,
  "logs": [
    {
      "timestamp": "2023-04-12T12:34:56.789Z",
      "source": "my-app",
      "environment": "production",
      "level": "error",
      "message": "Database connection failed",
      "metadata": {
        "userId": "abc123",
        "requestId": "def456"
      }
    },
    {
      "timestamp": "2023-04-12T12:35:01.234Z",
      "source": "my-app",
      "environment": "production",
      "level": "info",
      "message": "User logged in",
      "metadata": {
        "userId": "ghi789"
      }
    }
  ]
}
```

### Error Codes

| Status Code | Description |
| --- | --- |
| 400 | Bad Request - Invalid request parameters. |
| 401 | Unauthorized - Invalid API key or authentication. |
| 500 | Internal Server Error - An unexpected error occurred. |

## GET /logs/{id}

Retrieve a specific log entry by its ID.

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| id | string | Yes | The unique identifier of the log entry. |

### Response

```json
{
  "timestamp": "2023-04-12T12:34:56.789Z",
  "source": "my-app",
  "environment": "production",
  "level": "error",
  "message": "Database connection failed",
  "metadata": {
    "userId": "abc123",
    "requestId": "def456"
  }
}
```

### Error Codes

| Status Code | Description |
| --- | --- |
| 404 | Not Found - The log entry with the specified ID was not found. |
| 401 | Unauthorized - Invalid API key or authentication. |
| 500 | Internal Server Error - An unexpected error occurred. |

## DELETE /logs/{id}

Delete a specific log entry by its ID.

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| id | string | Yes | The unique identifier of the log entry. |

### Response

```json
{
  "success": true,
  "message": "Log entry deleted successfully"
}
```

### Error Codes

| Status Code | Description |
| --- | --- |
| 404 | Not Found - The log entry with the specified ID was not found. |
| 401 | Unauthorized - Invalid API key or authentication. |
| 500 | Internal Server Error - An unexpected error occurred. |