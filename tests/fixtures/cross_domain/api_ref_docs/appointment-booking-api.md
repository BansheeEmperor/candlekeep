---
title: Appointment Booking API
description: A RESTful API for managing appointments and bookings.
keywords: [appointment, booking, calendar, scheduling, availability]
category: api-reference
---

## GET /appointments
Retrieve a list of appointments.

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `start_date` | string | No | Filter appointments starting on or after this date (YYYY-MM-DD) |
| `end_date` | string | No | Filter appointments starting on or before this date (YYYY-MM-DD) |
| `status` | string | No | Filter appointments by status (e.g., "pending", "confirmed", "cancelled") |

### Response

```json
[
  {
    "id": "123456",
    "start_time": "2023-04-15T09:00:00Z",
    "end_time": "2023-04-15T10:00:00Z",
    "status": "confirmed",
    "customer": {
      "name": "John Doe",
      "email": "john@example.com",
      "phone": "555-1234"
    },
    "service": {
      "id": "abc123",
      "name": "Haircut",
      "duration": 60
    },
    "provider": {
      "id": "xyz789",
      "name": "Jane Smith"
    }
  },
  {
    "id": "789012",
    "start_time": "2023-04-16T14:30:00Z",
    "end_time": "2023-04-16T15:30:00Z",
    "status": "pending",
    "customer": {
      "name": "Jane Doe",
      "email": "jane@example.com",
      "phone": "555-5678"
    },
    "service": {
      "id": "def456",
      "name": "Massage",
      "duration": 60
    },
    "provider": {
      "id": "uvw123",
      "name": "Bob Johnson"
    }
  }
]
```

## POST /appointments
Create a new appointment.

### Request Body

```json
{
  "start_time": "2023-04-20T11:00:00Z",
  "end_time": "2023-04-20T12:00:00Z",
  "customer": {
    "name": "Alice Smith",
    "email": "alice@example.com",
    "phone": "555-9012"
  },
  "service": {
    "id": "ghi789"
  },
  "provider": {
    "id": "mno456"
  }
}
```

### Response

```json
{
  "id": "345678",
  "start_time": "2023-04-20T11:00:00Z",
  "end_time": "2023-04-20T12:00:00Z",
  "status": "pending",
  "customer": {
    "name": "Alice Smith",
    "email": "alice@example.com",
    "phone": "555-9012"
  },
  "service": {
    "id": "ghi789",
    "name": "Manicure",
    "duration": 60
  },
  "provider": {
    "id": "mno456",
    "name": "Charlie Davis"
  }
}
```

## PATCH /appointments/{id}
Update an existing appointment.

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | string | Yes | The ID of the appointment to update |

### Request Body

```json
{
  "status": "confirmed"
}
```

### Response

```json
{
  "id": "345678",
  "start_time": "2023-04-20T11:00:00Z",
  "end_time": "2023-04-20T12:00:00Z",
  "status": "confirmed",
  "customer": {
    "name": "Alice Smith",
    "email": "alice@example.com",
    "phone": "555-9012"
  },
  "service": {
    "id": "ghi789",
    "name": "Manicure",
    "duration": 60
  },
  "provider": {
    "id": "mno456",
    "name": "Charlie Davis"
  }
}
```

## DELETE /appointments/{id}
Cancel an existing appointment.

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | string | Yes | The ID of the appointment to cancel |

### Response

```json
{
  "id": "345678",
  "start_time": "2023-04-20T11:00:00Z",
  "end_time": "2023-04-20T12:00:00Z",
  "status": "cancelled",
  "customer": {
    "name": "Alice Smith",
    "email": "alice@example.com",
    "phone": "555-9012"
  },
  "service": {
    "id": "ghi789",
    "name": "Manicure",
    "duration": 60
  },
  "provider": {
    "id": "mno456",
    "name": "Charlie Davis"
  }
}
```

## Error Codes

| Status Code | Description |
| --- | --- |
| 400 Bad Request | The request was malformed or invalid. |
| 401 Unauthorized | The request did not include valid authentication credentials. |
| 404 Not Found | The requested resource was not found. |
| 409 Conflict | The request could not be completed due to a conflict with the current state of the resource. |
| 500 Internal Server Error | An unexpected error occurred on the server. |