---
title: Scheduling Calendar API
description: A RESTful API for managing user schedules and events.
keywords: [calendar, scheduling, events, appointments, calendar management]
category: api-reference
---

## `GET /calendars`
Retrieves a list of calendars associated with the authenticated user.

### Parameters
| Name | Type | Required | Description |
| ---- | ---- | -------- | ----------- |
| `start_date` | `string` | No | The start date to filter calendars (YYYY-MM-DD) |
| `end_date` | `string` | No | The end date to filter calendars (YYYY-MM-DD) |

### Response
```json
[
  {
    "id": "123456789",
    "name": "Personal Calendar",
    "description": "My personal schedule",
    "owner": "user@example.com",
    "created_at": "2023-04-01T12:00:00Z",
    "updated_at": "2023-04-05T09:30:00Z"
  },
  {
    "id": "987654321",
    "name": "Work Calendar",
    "description": "Calendar for work-related events",
    "owner": "user@example.com",
    "created_at": "2022-11-15T08:45:00Z",
    "updated_at": "2023-03-20T14:20:00Z"
  }
]
```

## `POST /calendars`
Creates a new calendar for the authenticated user.

### Request Body
```json
{
  "name": "Family Calendar",
  "description": "Calendar for family events and activities"
}
```

### Response
```json
{
  "id": "456789123",
  "name": "Family Calendar",
  "description": "Calendar for family events and activities",
  "owner": "user@example.com",
  "created_at": "2023-04-10T16:35:00Z",
  "updated_at": "2023-04-10T16:35:00Z"
}
```

## `GET /calendars/{calendar_id}/events`
Retrieves a list of events for a specific calendar.

### Parameters
| Name | Type | Required | Description |
| ---- | ---- | -------- | ----------- |
| `calendar_id` | `string` | Yes | The ID of the calendar to retrieve events for |
| `start_date` | `string` | No | The start date to filter events (YYYY-MM-DD) |
| `end_date` | `string` | No | The end date to filter events (YYYY-MM-DD) |

### Response
```json
[
  {
    "id": "789123456",
    "title": "Family Dinner",
    "description": "Dinner with the family at 7pm",
    "start_date": "2023-04-15T19:00:00Z",
    "end_date": "2023-04-15T21:00:00Z",
    "calendar_id": "456789123",
    "created_at": "2023-04-10T16:40:00Z",
    "updated_at": "2023-04-10T16:40:00Z"
  },
  {
    "id": "321654987",
    "title": "Weekly Team Meeting",
    "description": "Weekly team meeting to discuss project progress",
    "start_date": "2023-04-17T10:00:00Z",
    "end_date": "2023-04-17T11:00:00Z",
    "calendar_id": "987654321",
    "created_at": "2023-04-01T08:15:00Z",
    "updated_at": "2023-04-05T09:35:00Z"
  }
]
```

## `POST /calendars/{calendar_id}/events`
Creates a new event in a specific calendar.

### Parameters
| Name | Type | Required | Description |
| ---- | ---- | -------- | ----------- |
| `calendar_id` | `string` | Yes | The ID of the calendar to create the event in |

### Request Body
```json
{
  "title": "Doctor's Appointment",
  "description": "Annual checkup with Dr. Smith",
  "start_date": "2023-05-01T14:30:00Z",
  "end_date": "2023-05-01T15:30:00Z"
}
```

### Response
```json
{
  "id": "159753852",
  "title": "Doctor's Appointment",
  "description": "Annual checkup with Dr. Smith",
  "start_date": "2023-05-01T14:30:00Z",
  "end_date": "2023-05-01T15:30:00Z",
  "calendar_id": "456789123",
  "created_at": "2023-04-20T11:25:00Z",
  "updated_at": "2023-04-20T11:25:00Z"
}
```

## Error Codes
| Status Code | Description |
| ----------- | ----------- |
| 400 Bad Request | The request was malformed or missing required parameters |
| 401 Unauthorized | The request did not include valid authentication credentials |
| 403 Forbidden | The authenticated user is not authorized to perform the requested action |
| 404 Not Found | The requested resource could not be found |
| 500 Internal Server Error | An unexpected error occurred on the server |