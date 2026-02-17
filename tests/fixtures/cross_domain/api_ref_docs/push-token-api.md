---
title: Push Token API
description: API for creating, retrieving, and managing user push notification tokens
keywords: [push, notifications, mobile, tokens, devices]
category: api-reference
---

## POST /push-tokens
Create a new push notification token for a user.

### Parameters
None

### Request Body
```json
{
  "userId": "abc123",
  "platform": "ios",
  "token": "1234567890abcdef"
}
```

### Response
```json
{
  "id": "pt-123456",
  "userId": "abc123",
  "platform": "ios",
  "token": "1234567890abcdef",
  "createdAt": "2023-04-01T12:00:00Z"
}
```

### Error Codes
- `400 Bad Request`: Missing required fields or invalid data
- `409 Conflict`: Push token already exists for the given user and platform

## GET /push-tokens/{id}
Retrieve a push notification token by ID.

### Parameters
| Name | Type | Description |
| --- | --- | --- |
| `id` | string | The ID of the push token to retrieve |

### Response
```json
{
  "id": "pt-123456",
  "userId": "abc123",
  "platform": "ios",
  "token": "1234567890abcdef",
  "createdAt": "2023-04-01T12:00:00Z"
}
```

### Error Codes
- `404 Not Found`: Push token not found

## GET /users/{userId}/push-tokens
Retrieve all push notification tokens for a user.

### Parameters
| Name | Type | Description |
| --- | --- | --- |
| `userId` | string | The ID of the user to retrieve push tokens for |

### Response
```json
[
  {
    "id": "pt-123456",
    "userId": "abc123",
    "platform": "ios",
    "token": "1234567890abcdef",
    "createdAt": "2023-04-01T12:00:00Z"
  },
  {
    "id": "pt-789012",
    "userId": "abc123",
    "platform": "android",
    "token": "fedcba0987654321",
    "createdAt": "2023-04-02T09:30:00Z"
  }
]
```

### Error Codes
None

## DELETE /push-tokens/{id}
Delete a push notification token.

### Parameters
| Name | Type | Description |
| --- | --- | --- |
| `id` | string | The ID of the push token to delete |

### Response
```json
{
  "message": "Push token deleted successfully"
}
```

### Error Codes
- `404 Not Found`: Push token not found

## DELETE /users/{userId}/push-tokens
Delete all push notification tokens for a user.

### Parameters
| Name | Type | Description |
| --- | --- | --- |
| `userId` | string | The ID of the user to delete push tokens for |

### Response
```json
{
  "message": "All push tokens for user deleted successfully"
}
```

### Error Codes
None