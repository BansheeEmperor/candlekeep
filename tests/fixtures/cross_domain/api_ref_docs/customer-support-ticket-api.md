---
title: Customer Support Ticket API
description: API for creating, updating, and managing customer support tickets.
keywords: [customer support, tickets, helpdesk, incidents, requests]
category: api-reference
---

## Create Ticket
`POST /tickets`

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| subject | string | The subject of the ticket | Yes |
| description | string | The description of the ticket | Yes |
| customer_email | string | The email address of the customer | Yes |
| priority | string | The priority of the ticket (low, medium, high) | No |

### Request Body
```json
{
  "subject": "Broken product",
  "description": "The widget I purchased is not working as expected.",
  "customer_email": "john@example.com",
  "priority": "high"
}
```

### Response
```json
{
  "id": "123456",
  "subject": "Broken product",
  "description": "The widget I purchased is not working as expected.",
  "customer_email": "john@example.com",
  "priority": "high",
  "status": "open",
  "created_at": "2023-04-01T12:00:00Z",
  "updated_at": "2023-04-01T12:00:00Z"
}
```

### Error Codes
- `400 Bad Request`: Invalid request body or parameters
- `401 Unauthorized`: Invalid or missing authentication credentials
- `500 Internal Server Error`: Unexpected server error

## Get Ticket
`GET /tickets/{id}`

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| id | string | The ID of the ticket to retrieve | Yes |

### Response
```json
{
  "id": "123456",
  "subject": "Broken product",
  "description": "The widget I purchased is not working as expected.",
  "customer_email": "john@example.com",
  "priority": "high",
  "status": "open",
  "created_at": "2023-04-01T12:00:00Z",
  "updated_at": "2023-04-01T12:00:00Z"
}
```

### Error Codes
- `404 Not Found`: Ticket not found
- `401 Unauthorized`: Invalid or missing authentication credentials
- `500 Internal Server Error`: Unexpected server error

## Update Ticket
`PATCH /tickets/{id}`

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| id | string | The ID of the ticket to update | Yes |

### Request Body
```json
{
  "subject": "Broken product - update",
  "description": "The widget I purchased is still not working as expected.",
  "priority": "medium"
}
```

### Response
```json
{
  "id": "123456",
  "subject": "Broken product - update",
  "description": "The widget I purchased is still not working as expected.",
  "customer_email": "john@example.com",
  "priority": "medium",
  "status": "open",
  "created_at": "2023-04-01T12:00:00Z",
  "updated_at": "2023-04-02T09:30:00Z"
}
```

### Error Codes
- `404 Not Found`: Ticket not found
- `400 Bad Request`: Invalid request body or parameters
- `401 Unauthorized`: Invalid or missing authentication credentials
- `500 Internal Server Error`: Unexpected server error

## Close Ticket
`POST /tickets/{id}/close`

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| id | string | The ID of the ticket to close | Yes |

### Response
```json
{
  "id": "123456",
  "subject": "Broken product - update",
  "description": "The widget I purchased is still not working as expected.",
  "customer_email": "john@example.com",
  "priority": "medium",
  "status": "closed",
  "created_at": "2023-04-01T12:00:00Z",
  "updated_at": "2023-04-03T15:45:00Z"
}
```

### Error Codes
- `404 Not Found`: Ticket not found
- `400 Bad Request`: Ticket is already closed
- `401 Unauthorized`: Invalid or missing authentication credentials
- `500 Internal Server Error`: Unexpected server error