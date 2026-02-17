---
title: Replication API
description: RESTful API for managing data replication across multiple databases
keywords: [replication, data sync, database, backup, disaster recovery]
category: api-reference
---

## `GET /replications`
Retrieve a list of all active replication jobs.

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| `page` | integer | The page number to retrieve (default: 1) | No |
| `limit` | integer | The number of results to return per page (default: 20) | No |
| `status` | string | Filter results by replication status (e.g., "running", "paused", "error") | No |

### Response
```json
{
  "page": 1,
  "limit": 20,
  "total": 50,
  "replications": [
    {
      "id": "abc123",
      "source": "mysql://user:pass@source.db/data",
      "target": "postgresql://user:pass@target.db/data",
      "status": "running",
      "started_at": "2023-04-01T12:00:00Z",
      "last_sync": "2023-04-01T12:05:00Z"
    },
    {
      "id": "def456",
      "source": "mongodb://user:pass@source.db/data",
      "target": "cassandra://user:pass@target.db/data",
      "status": "paused",
      "started_at": "2023-03-15T09:30:00Z",
      "last_sync": "2023-03-31T18:45:00Z"
    }
  ]
}
```

## `GET /replications/{id}`
Retrieve details of a specific replication job.

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| `id` | string | The unique identifier of the replication job | Yes |

### Response
```json
{
  "id": "abc123",
  "source": "mysql://user:pass@source.db/data",
  "target": "postgresql://user:pass@target.db/data",
  "status": "running",
  "started_at": "2023-04-01T12:00:00Z",
  "last_sync": "2023-04-01T12:05:00Z",
  "sync_frequency": "5m",
  "last_error": null
}
```

## `POST /replications`
Create a new replication job.

### Request Body
```json
{
  "source": "mysql://user:pass@source.db/data",
  "target": "postgresql://user:pass@target.db/data",
  "sync_frequency": "5m",
  "initial_sync": true
}
```

### Response
```json
{
  "id": "abc123",
  "source": "mysql://user:pass@source.db/data",
  "target": "postgresql://user:pass@target.db/data",
  "status": "running",
  "started_at": "2023-04-01T12:00:00Z",
  "last_sync": "2023-04-01T12:00:00Z",
  "sync_frequency": "5m",
  "last_error": null
}
```

## `PATCH /replications/{id}`
Update an existing replication job.

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| `id` | string | The unique identifier of the replication job | Yes |

### Request Body
```json
{
  "sync_frequency": "10m",
  "status": "paused"
}
```

### Response
```json
{
  "id": "abc123",
  "source": "mysql://user:pass@source.db/data",
  "target": "postgresql://user:pass@target.db/data",
  "status": "paused",
  "started_at": "2023-04-01T12:00:00Z",
  "last_sync": "2023-04-01T12:05:00Z",
  "sync_frequency": "10m",
  "last_error": null
}
```

## `DELETE /replications/{id}`
Delete an existing replication job.

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| `id` | string | The unique identifier of the replication job | Yes |

### Response
```json
{
  "message": "Replication job deleted successfully"
}
```

## Error Codes
| Code | Description |
| --- | --- |
| 400 | Bad Request (e.g., invalid input data) |
| 404 | Not Found (the requested resource does not exist) |
| 409 | Conflict (e.g., trying to create a replication with a duplicate source/target) |
| 500 | Internal Server Error (an unexpected error occurred on the server) |