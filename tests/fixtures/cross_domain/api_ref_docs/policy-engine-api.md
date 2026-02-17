---
title: Policy Engine API
description: API for managing and evaluating policies in a policy engine system.
keywords: [policy engine, rules, decision management, policy evaluation, policy administration]
category: api-reference
---

## GET /policies
Retrieves a list of all policies.

### Parameters
| Name | Type | Required | Description |
| --- | --- | --- | --- |
| offset | integer | No | The number of policies to skip before returning results. |
| limit | integer | No | The maximum number of policies to return. |
| status | string | No | Filter policies by status (e.g., "active", "inactive"). |

### Response
```json
{
  "policies": [
    {
      "id": "policy-1",
      "name": "Default Policy",
      "description": "The default policy for the system.",
      "status": "active",
      "version": "1.0",
      "createdAt": "2023-04-01T12:00:00Z",
      "updatedAt": "2023-04-15T10:30:00Z"
    },
    {
      "id": "policy-2",
      "name": "Discount Policy",
      "description": "Policy for applying discounts to purchases.",
      "status": "active",
      "version": "2.1",
      "createdAt": "2022-11-20T08:45:00Z",
      "updatedAt": "2023-03-01T14:20:00Z"
    }
  ],
  "total": 2,
  "offset": 0,
  "limit": 10
}
```

### Error Codes
| Status Code | Description |
| --- | --- |
| 400 | Bad request (e.g., invalid query parameters) |
| 500 | Internal server error |

## POST /policies
Creates a new policy.

### Request Body
```json
{
  "name": "New Policy",
  "description": "This is a new policy.",
  "rules": [
    {
      "condition": "customer.age > 65",
      "action": "apply_discount(10)"
    },
    {
      "condition": "order.total > 1000",
      "action": "apply_discount(15)"
    }
  ]
}
```

### Response
```json
{
  "id": "policy-3",
  "name": "New Policy",
  "description": "This is a new policy.",
  "status": "active",
  "version": "1.0",
  "rules": [
    {
      "condition": "customer.age > 65",
      "action": "apply_discount(10)"
    },
    {
      "condition": "order.total > 1000",
      "action": "apply_discount(15)"
    }
  ],
  "createdAt": "2023-04-20T09:15:00Z",
  "updatedAt": "2023-04-20T09:15:00Z"
}
```

### Error Codes
| Status Code | Description |
| --- | --- |
| 400 | Bad request (e.g., missing required fields, invalid rule syntax) |
| 409 | Conflict (e.g., policy with the same name already exists) |
| 500 | Internal server error |

## GET /policies/{id}
Retrieves a specific policy by its ID.

### Parameters
| Name | Type | Required | Description |
| --- | --- | --- | --- |
| id | string | Yes | The ID of the policy to retrieve. |

### Response
```json
{
  "id": "policy-1",
  "name": "Default Policy",
  "description": "The default policy for the system.",
  "status": "active",
  "version": "1.0",
  "rules": [
    {
      "condition": "customer.age > 65",
      "action": "apply_discount(10)"
    },
    {
      "condition": "order.total > 1000",
      "action": "apply_discount(15)"
    }
  ],
  "createdAt": "2023-04-01T12:00:00Z",
  "updatedAt": "2023-04-15T10:30:00Z"
}
```

### Error Codes
| Status Code | Description |
| --- | --- |
| 404 | Not found (policy with the specified ID does not exist) |
| 500 | Internal server error |

## PUT /policies/{id}
Updates an existing policy.

### Parameters
| Name | Type | Required | Description |
| --- | --- | --- | --- |
| id | string | Yes | The ID of the policy to update. |

### Request Body
```json
{
  "name": "Updated Default Policy",
  "description": "The updated default policy for the system.",
  "rules": [
    {
      "condition": "customer.age > 60",
      "action": "apply_discount(15)"
    },
    {
      "condition": "order.total > 2000",
      "action": "apply_discount(20)"
    }
  ]
}
```

### Response
```json
{
  "id": "policy-1",
  "name": "Updated Default Policy",
  "description": "The updated default policy for the system.",
  "status": "active",
  "version": "2.0",
  "rules": [
    {
      "condition": "customer.age > 60",
      "action": "apply_discount(15)"
    },
    {
      "condition": "order.total > 2000",
      "action": "apply_discount(20)"
    }
  ],
  "createdAt": "2023-04-01T12:00:00Z",
  "updatedAt": "2023-04-20T11:45:00Z"
}
```

### Error Codes
| Status Code | Description |
| --- | --- |
| 404 | Not found (policy with the specified ID does not exist) |
| 400 | Bad request (e.g., invalid request body) |
| 500 | Internal server error |