---
title: Incident API
description: API for managing incident reports and response activities
keywords: [incident, report, response, event, issue]
category: api-reference
---

## GET /incidents
Retrieve a list of incident reports.

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| status | string | Filter incidents by status (open, closed, in-progress) | No |
| start_date | date | Filter incidents created on or after this date | No |
| end_date | date | Filter incidents created on or before this date | No |
| limit | integer | Maximum number of incidents to return (default 25, max 100) | No |
| offset | integer | Number of incidents to skip (for pagination) | No |

### Response
```json
{
  "incidents": [
    {
      "id": "abc123",
      "title": "Server Outage in US-East",
      "status": "open",
      "created_at": "2023-04-01T12:34:56Z",
      "updated_at": "2023-04-01T12:35:01Z",
      "priority": "high",
      "description": "Users in the US-East region are unable to access the application."
    },
    {
      "id": "def456",
      "title": "Billing system error",
      "status": "closed",
      "created_at": "2023-03-15T09:22:00Z",
      "updated_at": "2023-03-16T11:45:30Z",
      "priority": "medium",
      "description": "Some customers are unable to complete transactions due to a billing system error."
    }
  ],
  "total_count": 2,
  "limit": 25,
  "offset": 0
}
```

### Error Codes
| Status Code | Description |
| --- | --- |
| 400 | Invalid request parameters |
| 500 | Internal server error |

## POST /incidents
Create a new incident report.

### Request Body
```json
{
  "title": "Server Outage in US-East",
  "status": "open",
  "priority": "high",
  "description": "Users in the US-East region are unable to access the application."
}
```

### Response
```json
{
  "id": "abc123",
  "title": "Server Outage in US-East",
  "status": "open",
  "created_at": "2023-04-01T12:34:56Z",
  "updated_at": "2023-04-01T12:34:56Z",
  "priority": "high",
  "description": "Users in the US-East region are unable to access the application."
}
```

### Error Codes
| Status Code | Description |
| --- | --- |
| 400 | Invalid request body |
| 500 | Internal server error |

## GET /incidents/{id}
Retrieve details of a specific incident.

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| id | string | ID of the incident to retrieve | Yes |

### Response
```json
{
  "id": "abc123",
  "title": "Server Outage in US-East",
  "status": "open",
  "created_at": "2023-04-01T12:34:56Z",
  "updated_at": "2023-04-01T12:35:01Z",
  "priority": "high",
  "description": "Users in the US-East region are unable to access the application.",
  "updates": [
    {
      "id": "update123",
      "created_at": "2023-04-01T12:34:56Z",
      "author": "john_doe",
      "message": "Investigating the issue."
    },
    {
      "id": "update456",
      "created_at": "2023-04-01T12:35:01Z",
      "author": "jane_smith",
      "message": "Identified the root cause and working on a fix."
    }
  ]
}
```

### Error Codes
| Status Code | Description |
| --- | --- |
| 404 | Incident not found |
| 500 | Internal server error |

## PATCH /incidents/{id}
Update an existing incident report.

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| id | string | ID of the incident to update | Yes |

### Request Body
```json
{
  "status": "in-progress",
  "priority": "high",
  "description": "Investigating the issue and working on a fix."
}
```

### Response
```json
{
  "id": "abc123",
  "title": "Server Outage in US-East",
  "status": "in-progress",
  "created_at": "2023-04-01T12:34:56Z",
  "updated_at": "2023-04-01T12:35:10Z",
  "priority": "high",
  "description": "Investigating the issue and working on a fix."
}
```

### Error Codes
| Status Code | Description |
| --- | --- |
| 404 | Incident not found |
| 400 | Invalid request body |
| 500 | Internal server error |