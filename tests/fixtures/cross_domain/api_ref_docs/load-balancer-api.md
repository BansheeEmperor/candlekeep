---
title: Load Balancer API
description: API for managing load balancing services
keywords: [load balancer, traffic routing, high availability, scalability, health checks]
category: api-reference
---

## GET /load-balancers
Retrieves a list of all load balancers.

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| `page` | integer | The page number to retrieve (default: 1) | No |
| `per_page` | integer | The number of results per page (default: 20) | No |

### Response
```json
{
  "data": [
    {
      "id": "lb-123",
      "name": "Main Web Server LB",
      "ip_address": "10.0.0.5",
      "status": "active",
      "created_at": "2023-04-01T12:00:00Z"
    },
    {
      "id": "lb-456",
      "name": "API Service LB",
      "ip_address": "10.0.0.10",
      "status": "active",
      "created_at": "2023-03-15T09:30:00Z"
    }
  ],
  "meta": {
    "total_count": 2,
    "total_pages": 1
  }
}
```

## GET /load-balancers/{id}
Retrieves details of a specific load balancer.

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| `id` | string | The ID of the load balancer | Yes |

### Response
```json
{
  "data": {
    "id": "lb-123",
    "name": "Main Web Server LB",
    "ip_address": "10.0.0.5",
    "status": "active",
    "created_at": "2023-04-01T12:00:00Z",
    "updated_at": "2023-04-05T15:30:00Z",
    "backend_servers": [
      {
        "id": "srv-001",
        "ip_address": "192.168.1.10",
        "port": 80,
        "status": "healthy"
      },
      {
        "id": "srv-002",
        "ip_address": "192.168.1.11",
        "port": 80,
        "status": "healthy"
      }
    ],
    "health_checks": {
      "type": "http",
      "path": "/healthz",
      "port": 80,
      "interval": 10,
      "timeout": 5,
      "threshold": 3
    },
    "load_balancing_algorithm": "round-robin"
  }
}
```

## POST /load-balancers
Creates a new load balancer.

### Request Body
```json
{
  "name": "API Service LB",
  "ip_address": "10.0.0.10",
  "backend_servers": [
    {
      "ip_address": "192.168.1.20",
      "port": 8080
    },
    {
      "ip_address": "192.168.1.21",
      "port": 8080
    }
  ],
  "health_checks": {
    "type": "http",
    "path": "/healthz",
    "port": 8080,
    "interval": 10,
    "timeout": 5,
    "threshold": 2
  },
  "load_balancing_algorithm": "least-connections"
}
```

### Response
```json
{
  "data": {
    "id": "lb-456",
    "name": "API Service LB",
    "ip_address": "10.0.0.10",
    "status": "active",
    "created_at": "2023-04-10T09:45:00Z",
    "updated_at": "2023-04-10T09:45:00Z",
    "backend_servers": [
      {
        "id": "srv-003",
        "ip_address": "192.168.1.20",
        "port": 8080,
        "status": "healthy"
      },
      {
        "id": "srv-004",
        "ip_address": "192.168.1.21",
        "port": 8080,
        "status": "healthy"
      }
    ],
    "health_checks": {
      "type": "http",
      "path": "/healthz",
      "port": 8080,
      "interval": 10,
      "timeout": 5,
      "threshold": 2
    },
    "load_balancing_algorithm": "least-connections"
  }
}
```

## PATCH /load-balancers/{id}
Updates an existing load balancer.

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| `id` | string | The ID of the load balancer | Yes |

### Request Body
```json
{
  "name": "Main Web Server LB - Updated",
  "load_balancing_algorithm": "least-connections"
}
```

### Response
```json
{
  "data": {
    "id": "lb-123",
    "name": "Main Web Server LB - Updated",
    "ip_address": "10.0.0.5",
    "status": "active",
    "created_at": "2023-04-01T12:00:00Z",
    "updated_at": "2023-04-11T14:20:00Z",
    "backend_servers": [
      {
        "id": "srv-001",
        "ip_address": "192.168.1.10",
        "port": 80,
        "status": "healthy"
      },
      {
        "id": "srv-002",
        "ip_address": "192.168.1.11",
        "port": 80,
        "status": "healthy"
      }
    ],
    "health_checks": {
      "type": "http",
      "path": "/healthz",
      "port": 80,
      "interval": 10,
      "timeout": 5,
      "threshold": 3
    },
    "load_balancing_algorithm": "least-connections"
  }
}
```

## DELETE /load-balancers/{id}
Deletes a load balancer.

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| `id` | string | The ID of the load balancer | Yes |

### Response
```json
{
  "data": {
    "id": "lb-123",
    "name": "Main Web Server LB - Updated",
    "ip_address": "10.0.0.5",
    "status": "deleted",
    "created_at": "2023-04-01T12:00:00Z",
    "updated_at": "2023-04-11T14:25:00Z"
  }
}
```

### Error Codes
| HTTP Status | Error Code | Description |
| --- | --- | --- |
| 400 | `invalid_request` | The request body is invalid or missing required fields. |
| 404 | `not_found` | The requested load balancer was not found. |
| 409 | `conflict` | The requested operation cannot be completed due to a conflict. |
| 500 | `internal_server_error` | An unexpected error occurred on the server. |