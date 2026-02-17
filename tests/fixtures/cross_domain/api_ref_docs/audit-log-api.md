---
title: Audit Log API
description: Retrieve and manage audit logs for your organization.
keywords: [audit, logs, events, activity, security]
category: api-reference
---

## GET /audit-logs

Retrieve a list of audit logs.

### Parameters

| Name | Type | Description | Required |
| --- | --- | --- | --- |
| start_date | string | The start date for the audit log entries (ISO 8601 format) | No |
| end_date | string | The end date for the audit log entries (ISO 8601 format) | No |
| event_type | string | The type of event to filter by (e.g., "login", "file_upload") | No |
| user_id | string | The ID of the user to filter by | No |
| page | integer | The page number to retrieve (default is 1) | No |
| per_page | integer | The number of results to return per page (default is 25, max is 100) | No |

### Response

```json
{
  "total_count": 100,
  "page": 1,
  "per_page": 25,
  "data": [
    {
      "id": "123456789",
      "event_type": "login",
      "user_id": "abc123",
      "user_name": "John Doe",
      "timestamp": "2023-04-01T12:34:56Z",
      "details": {
        "ip_address": "192.168.1.100",
        "device": "Chrome on Windows"
      }
    },
    {
      "id": "987654321",
      "event_type": "file_upload",
      "user_id": "def456",
      "user_name": "Jane Smith",
      "timestamp": "2023-04-02T09:15:30Z",
      "details": {
        "file_name": "report.pdf",
        "file_size": 1024,
        "location": "/documents"
      }
    }
  ]
}
```

## GET /audit-logs/{id}

Retrieve a specific audit log entry.

### Parameters

| Name | Type | Description | Required |
| --- | --- | --- | --- |
| id | string | The ID of the audit log entry to retrieve | Yes |

### Response

```json
{
  "id": "123456789",
  "event_type": "login",
  "user_id": "abc123",
  "user_name": "John Doe",
  "timestamp": "2023-04-01T12:34:56Z",
  "details": {
    "ip_address": "192.168.1.100",
    "device": "Chrome on Windows"
  }
}
```

## POST /audit-logs

Create a new audit log entry.

### Request Body

```json
{
  "event_type": "file_upload",
  "user_id": "def456",
  "details": {
    "file_name": "report.pdf",
    "file_size": 1024,
    "location": "/documents"
  }
}
```

### Response

```json
{
  "id": "987654321",
  "event_type": "file_upload",
  "user_id": "def456",
  "user_name": "Jane Smith",
  "timestamp": "2023-04-02T09:15:30Z",
  "details": {
    "file_name": "report.pdf",
    "file_size": 1024,
    "location": "/documents"
  }
}
```

## DELETE /audit-logs/{id}

Delete a specific audit log entry.

### Parameters

| Name | Type | Description | Required |
| --- | --- | --- | --- |
| id | string | The ID of the audit log entry to delete | Yes |

### Response

```json
{
  "message": "Audit log entry deleted successfully."
}
```

## Error Codes

| Code | Description |
| --- | --- |
| 400 | Bad Request - The request was malformed or missing required parameters. |
| 401 | Unauthorized - The request did not include valid authentication credentials. |
| 403 | Forbidden - The user does not have permission to perform the requested action. |
| 404 | Not Found - The requested resource was not found. |
| 500 | Internal Server Error - An unexpected error occurred on the server. |