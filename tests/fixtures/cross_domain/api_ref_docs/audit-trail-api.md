---
title: Audit Trail API
description: API to access and manage the audit trail for your application.
keywords: [audit, trail, logs, events, activity, history]
category: api-reference
---

## GET /audit-trail
Retrieve a list of audit trail entries.

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| start_date | string | No | Filter events starting from this date (YYYY-MM-DD) |
| end_date | string | No | Filter events up to this date (YYYY-MM-DD) |
| user_id | string | No | Filter events by a specific user ID |
| event_type | string | No | Filter events by a specific event type |
| page | integer | No | Page number for pagination (default: 1) |
| per_page | integer | No | Number of results per page (default: 20, max: 100) |

### Response

```json
{
  "total_count": 125,
  "page": 1,
  "per_page": 20,
  "data": [
    {
      "id": "abc123",
      "user_id": "user123",
      "event_type": "user_login",
      "details": {
        "ip_address": "192.168.1.100",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
      },
      "created_at": "2023-04-01T10:30:00Z"
    },
    {
      "id": "def456",
      "user_id": "user456",
      "event_type": "user_update",
      "details": {
        "field_changed": "email",
        "old_value": "user@example.com",
        "new_value": "new_user@example.com"
      },
      "created_at": "2023-04-02T15:45:30Z"
    }
  ]
}
```

### Error Codes

| Status Code | Description |
| --- | --- |
| 400 | Bad request (e.g., invalid parameters) |
| 401 | Unauthorized (invalid or missing authentication credentials) |
| 403 | Forbidden (user not authorized to access this resource) |
| 500 | Internal server error |

## GET /audit-trail/{id}
Retrieve a specific audit trail entry by its ID.

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| id | string | Yes | The ID of the audit trail entry to retrieve |

### Response

```json
{
  "id": "abc123",
  "user_id": "user123",
  "event_type": "user_login",
  "details": {
    "ip_address": "192.168.1.100",
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
  },
  "created_at": "2023-04-01T10:30:00Z"
}
```

### Error Codes

| Status Code | Description |
| --- | --- |
| 404 | Not found (audit trail entry not found) |
| 401 | Unauthorized (invalid or missing authentication credentials) |
| 403 | Forbidden (user not authorized to access this resource) |
| 500 | Internal server error |

## POST /audit-trail
Create a new audit trail entry.

### Request Body

```json
{
  "user_id": "user123",
  "event_type": "user_login",
  "details": {
    "ip_address": "192.168.1.100",
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
  }
}
```

### Response

```json
{
  "id": "abc123",
  "user_id": "user123",
  "event_type": "user_login",
  "details": {
    "ip_address": "192.168.1.100",
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
  },
  "created_at": "2023-04-01T10:30:00Z"
}
```

### Error Codes

| Status Code | Description |
| --- | --- |
| 400 | Bad request (e.g., missing required fields) |
| 401 | Unauthorized (invalid or missing authentication credentials) |
| 403 | Forbidden (user not authorized to perform this action) |
| 500 | Internal server error |

## DELETE /audit-trail/{id}
Delete a specific audit trail entry by its ID.

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| id | string | Yes | The ID of the audit trail entry to delete |

### Response

```json
{
  "message": "Audit trail entry deleted successfully"
}
```

### Error Codes

| Status Code | Description |
| --- | --- |
| 404 | Not found (audit trail entry not found) |
| 401 | Unauthorized (invalid or missing authentication credentials) |
| 403 | Forbidden (user not authorized to perform this action) |
| 500 | Internal server error |