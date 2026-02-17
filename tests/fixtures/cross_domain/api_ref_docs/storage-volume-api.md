---
title: Storage Volume API
description: API for managing storage volumes
keywords: [storage, volume, disk, block, api]
category: api-reference
---

## GET /volumes
Retrieve a list of storage volumes.

### Parameters
| Name | Type | Description |
| --- | --- | --- |
| `page` | integer | Page number for pagination. Default is 1. |
| `per_page` | integer | Number of results per page. Default is 25, maximum is 100. |
| `name` | string | Filter volumes by name. |
| `status` | string | Filter volumes by status (e.g., "available", "in-use"). |

### Response
```json
{
  "volumes": [
    {
      "id": "vol-0123456789abcdef",
      "name": "my-volume",
      "size": 100,
      "status": "available",
      "created_at": "2023-04-01T12:00:00Z"
    },
    {
      "id": "vol-fedcba9876543210",
      "name": "backup-volume",
      "size": 500,
      "status": "in-use",
      "created_at": "2023-03-15T09:30:00Z"
    }
  ],
  "meta": {
    "total_count": 2,
    "page": 1,
    "per_page": 25
  }
}
```

## GET /volumes/{id}
Retrieve details of a specific storage volume.

### Parameters
| Name | Type | Description |
| --- | --- | --- |
| `id` | string | ID of the storage volume. |

### Response
```json
{
  "volume": {
    "id": "vol-0123456789abcdef",
    "name": "my-volume",
    "size": 100,
    "status": "available",
    "created_at": "2023-04-01T12:00:00Z",
    "attachments": []
  }
}
```

## POST /volumes
Create a new storage volume.

### Request Body
```json
{
  "name": "new-volume",
  "size": 200,
  "tags": {
    "environment": "production",
    "department": "engineering"
  }
}
```

### Response
```json
{
  "volume": {
    "id": "vol-newvolumeid123",
    "name": "new-volume",
    "size": 200,
    "status": "available",
    "created_at": "2023-04-05T15:30:00Z",
    "tags": {
      "environment": "production",
      "department": "engineering"
    }
  }
}
```

## PATCH /volumes/{id}
Update an existing storage volume.

### Parameters
| Name | Type | Description |
| --- | --- | --- |
| `id` | string | ID of the storage volume. |

### Request Body
```json
{
  "name": "updated-volume",
  "size": 250
}
```

### Response
```json
{
  "volume": {
    "id": "vol-0123456789abcdef",
    "name": "updated-volume",
    "size": 250,
    "status": "available",
    "created_at": "2023-04-01T12:00:00Z",
    "attachments": []
  }
}
```

## DELETE /volumes/{id}
Delete a storage volume.

### Parameters
| Name | Type | Description |
| --- | --- | --- |
| `id` | string | ID of the storage volume. |

### Response
```json
{
  "message": "Volume deleted successfully."
}
```

### Error Codes
| Status Code | Description |
| --- | --- |
| 400 Bad Request | Invalid request parameters. |
| 404 Not Found | Volume not found. |
| 409 Conflict | Volume is currently in use and cannot be deleted. |
| 500 Internal Server Error | An unexpected error occurred while processing the request. |