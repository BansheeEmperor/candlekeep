---
title: Notification Service API
description: API for managing user notifications
keywords: [notifications, alerts, messages, users, events]
category: api-reference
---

## GET /notifications

Retrieve a list of notifications for the current user.

### Parameters

| Name | Type | Description | Required |
| --- | --- | --- | --- |
| `page` | integer | Page number for pagination | No |
| `per_page` | integer | Number of results per page | No |
| `read` | boolean | Filter by read status | No |
| `type` | string | Filter by notification type | No |

### Response

```json
{
  "data": [
    {
      "id": "123456",
      "type": "new_message",
      "title": "New message from John Doe",
      "content": "John Doe sent you a new message",
      "read": false,
      "created_at": "2023-04-01T12:34:56Z"
    },
    {
      "id": "789012",
      "type": "account_update",
      "title": "Your account has been updated",
      "content": "Your account information has been successfully updated",
      "read": true,
      "created_at": "2023-03-15T09:12:34Z"
    }
  ],
  "meta": {
    "total": 25,
    "current_page": 1,
    "total_pages": 3
  }
}
```

### Error Codes

| Status Code | Description |
| --- | --- |
| 401 Unauthorized | The user is not authenticated |
| 403 Forbidden | The user is not authorized to access this resource |

## GET /notifications/{id}

Retrieve a specific notification by ID.

### Parameters

| Name | Type | Description | Required |
| --- | --- | --- | --- |
| `id` | string | The ID of the notification | Yes |

### Response

```json
{
  "data": {
    "id": "123456",
    "type": "new_message",
    "title": "New message from John Doe",
    "content": "John Doe sent you a new message",
    "read": false,
    "created_at": "2023-04-01T12:34:56Z"
  }
}
```

### Error Codes

| Status Code | Description |
| --- | --- |
| 404 Not Found | The notification with the specified ID was not found |

## POST /notifications/{id}/mark-read

Mark a specific notification as read.

### Parameters

| Name | Type | Description | Required |
| --- | --- | --- | --- |
| `id` | string | The ID of the notification | Yes |

### Response

```json
{
  "data": {
    "id": "123456",
    "type": "new_message",
    "title": "New message from John Doe",
    "content": "John Doe sent you a new message",
    "read": true,
    "created_at": "2023-04-01T12:34:56Z"
  }
}
```

### Error Codes

| Status Code | Description |
| --- | --- |
| 404 Not Found | The notification with the specified ID was not found |

## DELETE /notifications/{id}

Delete a specific notification.

### Parameters

| Name | Type | Description | Required |
| --- | --- | --- | --- |
| `id` | string | The ID of the notification | Yes |

### Response

```json
{
  "data": {
    "id": "123456",
    "type": "new_message",
    "title": "New message from John Doe",
    "content": "John Doe sent you a new message",
    "read": true,
    "created_at": "2023-04-01T12:34:56Z"
  }
}
```

### Error Codes

| Status Code | Description |
| --- | --- |
| 404 Not Found | The notification with the specified ID was not found |