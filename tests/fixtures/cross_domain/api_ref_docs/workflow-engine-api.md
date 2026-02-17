---
title: Workflow Engine API
description: API for managing and executing workflows in a distributed system.
keywords: [workflow, engine, automation, integration, task, process]
category: api-reference
---

## GET /workflows
Retrieve a list of all available workflows.

### Parameters
| Name | Type | Description |
| --- | --- | --- |
| `status` | `string` | (Optional) Filter workflows by status (e.g. "running", "completed", "failed") |
| `owner` | `string` | (Optional) Filter workflows by owner |
| `limit` | `integer` | (Optional) Limit the number of results returned |
| `offset` | `integer` | (Optional) Offset the results by a specific number |

### Response
```json
[
  {
    "id": "123456789",
    "name": "Order Processing",
    "status": "running",
    "owner": "john.doe@example.com",
    "startedAt": "2023-04-01T12:00:00Z",
    "updatedAt": "2023-04-01T12:10:00Z"
  },
  {
    "id": "987654321",
    "name": "Customer Onboarding",
    "status": "completed",
    "owner": "jane.smith@example.com",
    "startedAt": "2023-03-15T09:30:00Z",
    "completedAt": "2023-03-15T10:15:00Z"
  }
]
```

### Error Codes
| Code | Description |
| --- | --- |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 500 | Internal Server Error |

## POST /workflows
Create a new workflow.

### Request Body
```json
{
  "name": "Order Processing",
  "description": "Process a new order",
  "steps": [
    {
      "id": "receive-order",
      "name": "Receive Order",
      "type": "task",
      "handler": "order-received"
    },
    {
      "id": "validate-order",
      "name": "Validate Order",
      "type": "task",
      "handler": "order-validation"
    },
    {
      "id": "process-payment",
      "name": "Process Payment",
      "type": "task",
      "handler": "payment-processing"
    },
    {
      "id": "ship-order",
      "name": "Ship Order",
      "type": "task",
      "handler": "order-shipping"
    }
  ],
  "owner": "john.doe@example.com"
}
```

### Response
```json
{
  "id": "123456789",
  "name": "Order Processing",
  "status": "running",
  "owner": "john.doe@example.com",
  "startedAt": "2023-04-01T12:00:00Z"
}
```

### Error Codes
| Code | Description |
| --- | --- |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 500 | Internal Server Error |

## GET /workflows/{id}
Retrieve details of a specific workflow.

### Parameters
| Name | Type | Description |
| --- | --- | --- |
| `id` | `string` | The ID of the workflow to retrieve |

### Response
```json
{
  "id": "123456789",
  "name": "Order Processing",
  "description": "Process a new order",
  "status": "running",
  "owner": "john.doe@example.com",
  "startedAt": "2023-04-01T12:00:00Z",
  "updatedAt": "2023-04-01T12:10:00Z",
  "steps": [
    {
      "id": "receive-order",
      "name": "Receive Order",
      "type": "task",
      "status": "completed",
      "startedAt": "2023-04-01T12:00:00Z",
      "completedAt": "2023-04-01T12:02:00Z"
    },
    {
      "id": "validate-order",
      "name": "Validate Order",
      "type": "task",
      "status": "running",
      "startedAt": "2023-04-01T12:02:00Z"
    },
    {
      "id": "process-payment",
      "name": "Process Payment",
      "type": "task",
      "status": "pending",
      "startedAt": null
    },
    {
      "id": "ship-order",
      "name": "Ship Order",
      "type": "task",
      "status": "pending",
      "startedAt": null
    }
  ]
}
```

### Error Codes
| Code | Description |
| --- | --- |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 500 | Internal Server Error |

## POST /workflows/{id}/execute
Execute a workflow.

### Parameters
| Name | Type | Description |
| --- | --- | --- |
| `id` | `string` | The ID of the workflow to execute |

### Request Body
```json
{
  "input": {
    "order_id": "ABC123",
    "customer_name": "John Doe",
    "total_amount": 99.99
  }
}
```

### Response
```json
{
  "id": "123456789",
  "status": "running",
  "startedAt": "2023-04-01T12:00:00Z"
}
```

### Error Codes
| Code | Description |
| --- | --- |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 500 | Internal Server Error |