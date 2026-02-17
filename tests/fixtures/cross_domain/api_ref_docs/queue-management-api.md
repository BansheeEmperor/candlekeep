---
title: Queue Management API
description: API for managing customer queues in a retail or service environment.
keywords: [queue, queue management, customer flow, wait time, ticket]
category: api-reference
---

## GET /queues
Retrieves a list of all active queues.

### Parameters
None

### Response
```json
[
  {
    "id": "123456789",
    "name": "Main Lobby",
    "current_ticket": 42,
    "estimated_wait_time": 15
  },
  {
    "id": "987654321",
    "name": "Customer Service",
    "current_ticket": 18,
    "estimated_wait_time": 30
  }
]
```

### Error Codes
- `400 Bad Request`: Invalid request parameters
- `500 Internal Server Error`: Server error occurred

## GET /queues/{queueId}
Retrieves details for a specific queue.

### Parameters
| Name | Type | Description |
| --- | --- | --- |
| `queueId` | string | Unique identifier of the queue |

### Response
```json
{
  "id": "123456789",
  "name": "Main Lobby",
  "current_ticket": 42,
  "estimated_wait_time": 15,
  "tickets": [
    {
      "id": "A001",
      "created_at": "2023-04-01T10:15:00Z",
      "status": "waiting"
    },
    {
      "id": "A002",
      "created_at": "2023-04-01T10:16:30Z",
      "status": "waiting"
    },
    {
      "id": "A003",
      "created_at": "2023-04-01T10:18:45Z",
      "status": "served"
    }
  ]
}
```

### Error Codes
- `400 Bad Request`: Invalid request parameters
- `404 Not Found`: Queue not found
- `500 Internal Server Error`: Server error occurred

## POST /queues
Creates a new queue.

### Request Body
```json
{
  "name": "VIP Lounge",
  "initial_ticket_number": 100
}
```

### Response
```json
{
  "id": "555555555",
  "name": "VIP Lounge",
  "current_ticket": 100,
  "estimated_wait_time": 0
}
```

### Error Codes
- `400 Bad Request`: Invalid request body
- `409 Conflict`: Queue with the same name already exists
- `500 Internal Server Error`: Server error occurred

## PUT /queues/{queueId}
Updates an existing queue.

### Parameters
| Name | Type | Description |
| --- | --- | --- |
| `queueId` | string | Unique identifier of the queue |

### Request Body
```json
{
  "name": "Premium Lounge"
}
```

### Response
```json
{
  "id": "555555555",
  "name": "Premium Lounge",
  "current_ticket": 100,
  "estimated_wait_time": 0
}
```

### Error Codes
- `400 Bad Request`: Invalid request parameters or body
- `404 Not Found`: Queue not found
- `500 Internal Server Error`: Server error occurred

## POST /queues/{queueId}/tickets
Adds a new ticket to a queue.

### Parameters
| Name | Type | Description |
| --- | --- | --- |
| `queueId` | string | Unique identifier of the queue |

### Response
```json
{
  "id": "A004",
  "created_at": "2023-04-01T10:20:00Z",
  "status": "waiting"
}
```

### Error Codes
- `400 Bad Request`: Invalid request parameters
- `404 Not Found`: Queue not found
- `500 Internal Server Error`: Server error occurred