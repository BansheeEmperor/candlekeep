---
title: Backup and Restore API
description: API for managing backups and restoring data
keywords: [backup, restore, data, recovery, snapshot]
category: api-reference
---

## GET /backups
Retrieve a list of available backups.

### Parameters
| Name | Type | Description |
| --- | --- | --- |
| `page` | integer | Page number for pagination (default: 1) |
| `limit` | integer | Number of results per page (default: 20, max: 100) |

### Response
```json
{
  "data": [
    {
      "id": "b1234567",
      "created_at": "2023-04-01T12:00:00Z",
      "size": 1024000000,
      "status": "completed"
    },
    {
      "id": "b7654321",
      "created_at": "2023-03-15T09:30:00Z",
      "size": 512000000,
      "status": "in_progress"
    }
  ],
  "meta": {
    "total": 2,
    "page": 1,
    "limit": 20
  }
}
```

## POST /backups
Create a new backup.

### Request Body
```json
{
  "name": "Daily Backup",
  "description": "Backup of production database",
  "schedule": "0 2 * * *"
}
```

### Response
```json
{
  "id": "b9876543",
  "created_at": "2023-04-02T02:00:00Z",
  "size": 0,
  "status": "in_progress"
}
```

## GET /backups/{id}
Retrieve details of a specific backup.

### Parameters
| Name | Type | Description |
| --- | --- | --- |
| `id` | string | ID of the backup |

### Response
```json
{
  "id": "b1234567",
  "created_at": "2023-04-01T12:00:00Z",
  "size": 1024000000,
  "status": "completed",
  "download_url": "https://example.com/backups/b1234567.zip"
}
```

## POST /restore
Restore data from a backup.

### Request Body
```json
{
  "backup_id": "b1234567",
  "target_environment": "production"
}
```

### Response
```json
{
  "id": "r987654",
  "backup_id": "b1234567",
  "status": "in_progress",
  "estimated_completion_time": "2023-04-02T14:30:00Z"
}
```

## GET /restore/{id}
Check the status of a restore operation.

### Parameters
| Name | Type | Description |
| --- | --- | --- |
| `id` | string | ID of the restore operation |

### Response
```json
{
  "id": "r987654",
  "backup_id": "b1234567",
  "status": "completed",
  "start_time": "2023-04-02T12:00:00Z",
  "end_time": "2023-04-02T14:15:00Z"
}
```

## Error Codes
| HTTP Status | Error Code | Description |
| --- | --- | --- |
| 400 | `INVALID_REQUEST` | The request is invalid or missing required parameters. |
| 404 | `RESOURCE_NOT_FOUND` | The requested resource (backup or restore operation) was not found. |
| 500 | `INTERNAL_SERVER_ERROR` | An unexpected error occurred on the server. |