---
title: Cluster Management API
description: API for managing Kubernetes clusters
keywords: [kubernetes, cluster, management, api]
category: api-reference
---

## GET /clusters
Retrieve a list of all Kubernetes clusters.

### Parameters
| Name | Type | Description |
| --- | --- | --- |
| `page` | `integer` | Page number for pagination (default: 1) |
| `per_page` | `integer` | Number of results per page (default: 20) |

### Response
```json
{
  "data": [
    {
      "id": "cluster-1",
      "name": "Development Cluster",
      "provider": "gcp",
      "region": "us-west1",
      "nodes": 5,
      "status": "running"
    },
    {
      "id": "cluster-2",
      "name": "Production Cluster",
      "provider": "aws",
      "region": "us-east1",
      "nodes": 10,
      "status": "running"
    }
  ],
  "meta": {
    "total_count": 2,
    "page": 1,
    "per_page": 20
  }
}
```

## POST /clusters
Create a new Kubernetes cluster.

### Request Body
```json
{
  "name": "New Cluster",
  "provider": "gcp",
  "region": "us-west1",
  "node_count": 3
}
```

### Response
```json
{
  "id": "cluster-3",
  "name": "New Cluster",
  "provider": "gcp",
  "region": "us-west1",
  "nodes": 3,
  "status": "provisioning"
}
```

## GET /clusters/{id}
Retrieve details of a specific Kubernetes cluster.

### Parameters
| Name | Type | Description |
| --- | --- | --- |
| `id` | `string` | ID of the cluster |

### Response
```json
{
  "id": "cluster-1",
  "name": "Development Cluster",
  "provider": "gcp",
  "region": "us-west1",
  "nodes": 5,
  "status": "running",
  "created_at": "2023-04-01T12:00:00Z",
  "updated_at": "2023-04-15T10:30:00Z"
}
```

## PATCH /clusters/{id}
Update an existing Kubernetes cluster.

### Parameters
| Name | Type | Description |
| --- | --- | --- |
| `id` | `string` | ID of the cluster |

### Request Body
```json
{
  "name": "Updated Cluster",
  "node_count": 5
}
```

### Response
```json
{
  "id": "cluster-1",
  "name": "Updated Cluster",
  "provider": "gcp",
  "region": "us-west1",
  "nodes": 5,
  "status": "updating"
}
```

## DELETE /clusters/{id}
Delete a Kubernetes cluster.

### Parameters
| Name | Type | Description |
| --- | --- | --- |
| `id` | `string` | ID of the cluster |

### Response
```json
{
  "message": "Cluster 'cluster-1' is being deleted."
}
```

### Error Codes
| Status Code | Description |
| --- | --- |
| 400 Bad Request | Invalid request parameters |
| 404 Not Found | Cluster not found |
| 409 Conflict | Cluster cannot be deleted while in use |
| 500 Internal Server Error | Internal server error |