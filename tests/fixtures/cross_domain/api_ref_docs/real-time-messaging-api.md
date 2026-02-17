---
title: Real-Time Messaging API
description: A powerful API for building real-time messaging features in your application.
keywords: [real-time, messaging, chat, websocket, push]
category: api-reference
---

## `GET /messages`
Retrieve a paginated list of messages.

### Parameters
| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `channel_id` | string | Yes | The ID of the channel to retrieve messages for. |
| `page` | integer | No | The page number to retrieve (default: 1). |
| `per_page` | integer | No | The number of messages to return per page (default: 20, max: 100). |

### Response
```json
{
  "messages": [
    {
      "id": "123456789",
      "channel_id": "abc123",
      "user_id": "user123",
      "content": "Hello, world!",
      "created_at": "2023-04-01T12:34:56Z"
    },
    {
      "id": "987654321",
      "channel_id": "abc123",
      "user_id": "user456",
      "content": "This is another message.",
      "created_at": "2023-04-01T12:35:00Z"
    }
  ],
  "pagination": {
    "current_page": 1,
    "total_pages": 10,
    "total_count": 200
  }
}
```

### Error Codes
| Code | Description |
| --- | --- |
| 400 | Invalid request parameters. |
| 403 | Forbidden access to the requested channel. |
| 404 | Channel not found. |

## `POST /messages`
Create a new message in a channel.

### Request Body
```json
{
  "channel_id": "abc123",
  "user_id": "user123",
  "content": "Hello, world!"
}
```

### Response
```json
{
  "id": "123456789",
  "channel_id": "abc123",
  "user_id": "user123",
  "content": "Hello, world!",
  "created_at": "2023-04-01T12:34:56Z"
}
```

### Error Codes
| Code | Description |
| --- | --- |
| 400 | Invalid request body. |
| 403 | Forbidden access to the requested channel. |
| 404 | Channel not found. |

## `GET /channels`
Retrieve a list of channels the user is a member of.

### Parameters
| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `user_id` | string | Yes | The ID of the user to retrieve channels for. |

### Response
```json
{
  "channels": [
    {
      "id": "abc123",
      "name": "General",
      "description": "The main channel for team discussions.",
      "member_count": 20
    },
    {
      "id": "def456",
      "name": "Random",
      "description": "A place to share random thoughts and ideas.",
      "member_count": 15
    }
  ]
}
```

### Error Codes
| Code | Description |
| --- | --- |
| 400 | Invalid request parameters. |
| 403 | Forbidden access to the user's channels. |

## `POST /channels`
Create a new channel.

### Request Body
```json
{
  "name": "New Channel",
  "description": "A new channel for team discussions.",
  "user_ids": ["user123", "user456", "user789"]
}
```

### Response
```json
{
  "id": "ghi789",
  "name": "New Channel",
  "description": "A new channel for team discussions.",
  "member_count": 3
}
```

### Error Codes
| Code | Description |
| --- | --- |
| 400 | Invalid request body. |
| 403 | Forbidden to create a new channel. |