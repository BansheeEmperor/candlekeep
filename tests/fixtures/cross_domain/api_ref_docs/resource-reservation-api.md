---
title: Resource Reservation API
description: API for reserving and managing resources.
keywords: [resource, reservation, booking, scheduling, availability]
category: api-reference
---

## GET /resources
Retrieve a list of available resources.

### Parameters
| Name | Type | Description |
| --- | --- | --- |
| type | string | (optional) Filter resources by type |
| location | string | (optional) Filter resources by location |
| availability | string | (optional) Filter resources by availability (e.g. "available", "booked") |

### Response
```json
[
  {
    "id": "123456",
    "name": "Conference Room A",
    "type": "meeting_room",
    "location": "Building 1, Floor 2",
    "capacity": 10,
    "availability": "available"
  },
  {
    "id": "789012",
    "name": "Projector Cart",
    "type": "equipment",
    "location": "AV Storage",
    "availability": "booked"
  }
]
```

## POST /reservations
Create a new resource reservation.

### Request Body
```json
{
  "resourceId": "123456",
  "startTime": "2023-04-15T09:00:00Z",
  "endTime": "2023-04-15T10:00:00Z",
  "purpose": "Team meeting",
  "userId": "abc123"
}
```

### Response
```json
{
  "id": "987654",
  "resourceId": "123456",
  "startTime": "2023-04-15T09:00:00Z",
  "endTime": "2023-04-15T10:00:00Z",
  "purpose": "Team meeting",
  "userId": "abc123",
  "status": "confirmed"
}
```

## GET /reservations
Retrieve a list of reservations.

### Parameters
| Name | Type | Description |
| --- | --- | --- |
| resourceId | string | (optional) Filter reservations by resource |
| userId | string | (optional) Filter reservations by user |
| status | string | (optional) Filter reservations by status (e.g. "confirmed", "pending", "cancelled") |
| startTime | string | (optional) Filter reservations by start time |
| endTime | string | (optional) Filter reservations by end time |

### Response
```json
[
  {
    "id": "987654",
    "resourceId": "123456",
    "startTime": "2023-04-15T09:00:00Z",
    "endTime": "2023-04-15T10:00:00Z",
    "purpose": "Team meeting",
    "userId": "abc123",
    "status": "confirmed"
  },
  {
    "id": "456789",
    "resourceId": "789012",
    "startTime": "2023-04-16T14:00:00Z",
    "endTime": "2023-04-16T15:00:00Z",
    "purpose": "Presentation setup",
    "userId": "def456",
    "status": "pending"
  }
]
```

## PATCH /reservations/{id}
Update an existing resource reservation.

### Parameters
| Name | Type | Description |
| --- | --- | --- |
| id | string | The ID of the reservation to update |

### Request Body
```json
{
  "startTime": "2023-04-15T09:30:00Z",
  "endTime": "2023-04-15T10:30:00Z",
  "purpose": "Team meeting (rescheduled)"
}
```

### Response
```json
{
  "id": "987654",
  "resourceId": "123456",
  "startTime": "2023-04-15T09:30:00Z",
  "endTime": "2023-04-15T10:30:00Z",
  "purpose": "Team meeting (rescheduled)",
  "userId": "abc123",
  "status": "confirmed"
}
```

## DELETE /reservations/{id}
Cancel an existing resource reservation.

### Parameters
| Name | Type | Description |
| --- | --- | --- |
| id | string | The ID of the reservation to cancel |

### Response
```json
{
  "id": "987654",
  "resourceId": "123456",
  "startTime": "2023-04-15T09:30:00Z",
  "endTime": "2023-04-15T10:30:00Z",
  "purpose": "Team meeting (rescheduled)",
  "userId": "abc123",
  "status": "cancelled"
}
```

### Error Codes
| HTTP Status | Error Code | Description |
| --- | --- | --- |
| 400 | INVALID_REQUEST | The request body or parameters are invalid. |
| 404 | RESOURCE_NOT_FOUND | The requested resource or reservation was not found. |
| 409 | CONFLICT | The requested operation cannot be completed due to a conflict (e.g., the resource is already booked). |
| 500 | INTERNAL_SERVER_ERROR | An unexpected error occurred on the server. |