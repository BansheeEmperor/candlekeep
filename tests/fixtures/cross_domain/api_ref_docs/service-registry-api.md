---
title: Service Registry API
description: API for managing service registrations and discovery
keywords: [service registry, service discovery, microservices, cloud, REST API]
category: api-reference
---

## GET /services
Retrieve a list of all registered services.

### Parameters
| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| page | integer | The page number to retrieve | No |
| limit | integer | The number of results to return per page | No |
| name | string | Filter services by name | No |
| tags | string | Filter services by tags (comma-separated) | No |

### Response
```json
{
  "total": 25,
  "page": 1,
  "limit": 10,
  "services": [
    {
      "id": "abc123",
      "name": "user-service",
      "version": "v1.2.3",
      "description": "User management service",
      "tags": ["user", "profile"],
      "endpoints": [
        {
          "path": "/users",
          "method": "GET"
        },
        {
          "path": "/users/{id}",
          "method": "GET"
        }
      ],
      "metadata": {
        "owner": "engineering-team-a",
        "contact": "team-a@company.com"
      }
    },
    {
      "id": "def456",
      "name": "order-service",
      "version": "v2.0.0",
      "description": "Order processing service",
      "tags": ["order", "ecommerce"],
      "endpoints": [
        {
          "path": "/orders",
          "method": "GET"
        },
        {
          "path": "/orders",
          "method": "POST"
        }
      ],
      "metadata": {
        "owner": "engineering-team-b",
        "contact": "team-b@company.com"
      }
    }
  ]
}
```

## POST /services
Register a new service.

### Request Body
```json
{
  "name": "my-service",
  "version": "v1.0.0",
  "description": "My new service",
  "tags": ["my-tag", "another-tag"],
  "endpoints": [
    {
      "path": "/my-endpoint",
      "method": "GET"
    }
  ],
  "metadata": {
    "owner": "my-team",
    "contact": "my-team@company.com"
  }
}
```

### Response
```json
{
  "id": "ghi789",
  "name": "my-service",
  "version": "v1.0.0",
  "description": "My new service",
  "tags": ["my-tag", "another-tag"],
  "endpoints": [
    {
      "path": "/my-endpoint",
      "method": "GET"
    }
  ],
  "metadata": {
    "owner": "my-team",
    "contact": "my-team@company.com"
  }
}
```

## GET /services/{id}
Retrieve details of a specific service.

### Parameters
| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| id | string | The unique identifier of the service | Yes |

### Response
```json
{
  "id": "abc123",
  "name": "user-service",
  "version": "v1.2.3",
  "description": "User management service",
  "tags": ["user", "profile"],
  "endpoints": [
    {
      "path": "/users",
      "method": "GET"
    },
    {
      "path": "/users/{id}",
      "method": "GET"
    }
  ],
  "metadata": {
    "owner": "engineering-team-a",
    "contact": "team-a@company.com"
  }
}
```

## DELETE /services/{id}
Unregister a service.

### Parameters
| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| id | string | The unique identifier of the service | Yes |

### Response
```json
{
  "message": "Service 'abc123' has been unregistered."
}
```

## Error Codes
| Code | Description |
| ---- | ----------- |
| 400 | Bad Request - Invalid input data |
| 404 | Not Found - Service not found |
| 409 | Conflict - Service already registered |
| 500 | Internal Server Error - An unexpected error occurred |