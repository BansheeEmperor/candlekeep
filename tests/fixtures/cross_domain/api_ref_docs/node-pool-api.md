---
title: Node Pool API
description: Manage node pools for your Kubernetes clusters
keywords:
  - kubernetes
  - node pool
  - cluster
  - api
  - cloud
category: api-reference
---

## List Node Pools

`GET /node-pools`

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `cluster_id` | string | true | The ID of the cluster to list node pools for |
| `page` | integer | false | The page number to retrieve (default: 1) |
| `per_page` | integer | false | The number of results to return per page (default: 20, max: 100) |

### Response

```json
{
  "data": [
    {
      "id": "np-abc123",
      "name": "default-pool",
      "cluster_id": "c-def456",
      "node_count": 3,
      "instance_type": "n1-standard-4",
      "autoscaling": {
        "min_nodes": 2,
        "max_nodes": 5
      },
      "created_at": "2023-04-01T12:00:00Z",
      "updated_at": "2023-04-15T10:30:00Z"
    },
    {
      "id": "np-ghi789",
      "name": "gpu-pool",
      "cluster_id": "c-def456",
      "node_count": 2,
      "instance_type": "n1-highmem-8",
      "autoscaling": {
        "min_nodes": 1,
        "max_nodes": 3
      },
      "created_at": "2023-03-15T08:45:00Z",
      "updated_at": "2023-04-10T14:20:00Z"
    }
  ],
  "meta": {
    "total_count": 2,
    "total_pages": 1,
    "current_page": 1
  }
}
```

## Create a Node Pool

`POST /node-pools`

### Request Body

```json
{
  "name": "new-pool",
  "cluster_id": "c-def456",
  "node_count": 3,
  "instance_type": "n1-standard-4",
  "autoscaling": {
    "min_nodes": 2,
    "max_nodes": 5
  }
}
```

### Response

```json
{
  "id": "np-jkl012",
  "name": "new-pool",
  "cluster_id": "c-def456",
  "node_count": 3,
  "instance_type": "n1-standard-4",
  "autoscaling": {
    "min_nodes": 2,
    "max_nodes": 5
  },
  "created_at": "2023-04-20T09:15:00Z",
  "updated_at": "2023-04-20T09:15:00Z"
}
```

## Get a Node Pool

`GET /node-pools/{id}`

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | string | true | The ID of the node pool to retrieve |

### Response

```json
{
  "id": "np-abc123",
  "name": "default-pool",
  "cluster_id": "c-def456",
  "node_count": 3,
  "instance_type": "n1-standard-4",
  "autoscaling": {
    "min_nodes": 2,
    "max_nodes": 5
  },
  "created_at": "2023-04-01T12:00:00Z",
  "updated_at": "2023-04-15T10:30:00Z"
}
```

## Update a Node Pool

`PATCH /node-pools/{id}`

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | string | true | The ID of the node pool to update |

### Request Body

```json
{
  "name": "updated-pool",
  "node_count": 4,
  "autoscaling": {
    "min_nodes": 3,
    "max_nodes": 6
  }
}
```

### Response

```json
{
  "id": "np-abc123",
  "name": "updated-pool",
  "cluster_id": "c-def456",
  "node_count": 4,
  "instance_type": "n1-standard-4",
  "autoscaling": {
    "min_nodes": 3,
    "max_nodes": 6
  },
  "created_at": "2023-04-01T12:00:00Z",
  "updated_at": "2023-04-20T11:45:00Z"
}
```

## Delete a Node Pool

`DELETE /node-pools/{id}`

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | string | true | The ID of the node pool to delete |

### Response

```json
{
  "message": "Node pool deleted successfully"
}
```

### Error Codes

| Status Code | Error Message | Description |
| --- | --- | --- |
| 400 | `invalid_request` | The request body is invalid or missing required fields |
| 404 | `not_found` | The requested node pool or cluster does not exist |
| 409 | `conflict` | The requested operation cannot be completed due to a conflict |
| 500 | `internal_server_error` | An unexpected error occurred on the server |