---
title: Error Tracking API
description: API for tracking and managing application errors
keywords: [error tracking, error management, exception handling, bug reporting, monitoring]
category: api-reference
---

## Get Errors
`GET /errors`

### Parameters

| Name | Type | Description | Required |
| --- | --- | --- | --- |
| `page` | integer | Page number for pagination | No |
| `limit` | integer | Number of results per page | No |
| `project_id` | string | Filter by project ID | No |
| `status` | string | Filter by error status (e.g., "new", "acknowledged", "resolved") | No |
| `severity` | string | Filter by error severity (e.g., "critical", "high", "medium", "low") | No |

### Response
```json
{
  "total_count": 100,
  "page": 1,
  "limit": 20,
  "errors": [
    {
      "id": "1234abcd",
      "project_id": "project-123",
      "message": "NullPointerException in UserController.java:42",
      "stack_trace": "...",
      "status": "new",
      "severity": "high",
      "created_at": "2023-04-01T12:34:56Z",
      "updated_at": "2023-04-01T12:34:56Z"
    },
    {
      "id": "5678efgh",
      "project_id": "project-456",
      "message": "TypeError in utils.js:120",
      "stack_trace": "...",
      "status": "acknowledged",
      "severity": "medium",
      "created_at": "2023-03-15T09:12:34Z",
      "updated_at": "2023-03-16T11:22:33Z"
    }
  ]
}
```

## Create Error
`POST /errors`

### Request Body
```json
{
  "project_id": "project-123",
  "message": "NullPointerException in UserController.java:42",
  "stack_trace": "...",
  "severity": "high"
}
```

### Response
```json
{
  "id": "1234abcd",
  "project_id": "project-123",
  "message": "NullPointerException in UserController.java:42",
  "stack_trace": "...",
  "status": "new",
  "severity": "high",
  "created_at": "2023-04-01T12:34:56Z",
  "updated_at": "2023-04-01T12:34:56Z"
}
```

## Update Error
`PATCH /errors/{id}`

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| `id` | string | ID of the error to update | Yes |

### Request Body
```json
{
  "status": "acknowledged",
  "severity": "medium"
}
```

### Response
```json
{
  "id": "1234abcd",
  "project_id": "project-123",
  "message": "NullPointerException in UserController.java:42",
  "stack_trace": "...",
  "status": "acknowledged",
  "severity": "medium",
  "created_at": "2023-04-01T12:34:56Z",
  "updated_at": "2023-04-02T09:45:12Z"
}
```

## Delete Error
`DELETE /errors/{id}`

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| `id` | string | ID of the error to delete | Yes |

### Response
```json
{
  "message": "Error deleted successfully"
}
```

## Error Codes
| Status Code | Description |
| --- | --- |
| 400 Bad Request | Invalid request parameters or body |
| 401 Unauthorized | Missing or invalid authentication credentials |
| 403 Forbidden | Insufficient permissions to perform the requested action |
| 404 Not Found | The requested resource was not found |
| 500 Internal Server Error | An unexpected error occurred on the server |