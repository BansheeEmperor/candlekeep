---
title: Database Instance API
description: Manage your database instances programmatically.
keywords: [database, instance, management, api, cloud]
category: api-reference
---

## GET /databases
Retrieve a list of all database instances.

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| page | integer | The page number to retrieve. | No |
| per_page | integer | The number of results to return per page. | No |

### Response
```json
{
  "data": [
    {
      "id": "db-123",
      "name": "my-database",
      "engine": "postgresql",
      "version": "12.7",
      "status": "running",
      "created_at": "2023-04-01T12:00:00Z"
    },
    {
      "id": "db-456",
      "name": "analytics-db",
      "engine": "mysql",
      "version": "8.0.27",
      "status": "stopped",
      "created_at": "2022-11-15T09:30:00Z"
    }
  ],
  "meta": {
    "total": 2,
    "page": 1,
    "per_page": 10
  }
}
```

## GET /databases/{id}
Retrieve details of a specific database instance.

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| id | string | The ID of the database instance. | Yes |

### Response
```json
{
  "data": {
    "id": "db-123",
    "name": "my-database",
    "engine": "postgresql",
    "version": "12.7",
    "status": "running",
    "host": "db-123.example.com",
    "port": 5432,
    "size": 5,
    "storage_type": "ssd",
    "created_at": "2023-04-01T12:00:00Z",
    "updated_at": "2023-04-15T14:30:00Z"
  }
}
```

## POST /databases
Create a new database instance.

### Request Body
```json
{
  "name": "my-new-database",
  "engine": "postgresql",
  "version": "12.7",
  "size": 10,
  "storage_type": "ssd"
}
```

### Response
```json
{
  "data": {
    "id": "db-789",
    "name": "my-new-database",
    "engine": "postgresql",
    "version": "12.7",
    "status": "provisioning",
    "host": "db-789.example.com",
    "port": 5432,
    "size": 10,
    "storage_type": "ssd",
    "created_at": "2023-04-20T09:15:00Z"
  }
}
```

## PATCH /databases/{id}
Update the configuration of a database instance.

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| id | string | The ID of the database instance. | Yes |

### Request Body
```json
{
  "name": "updated-database-name",
  "size": 15
}
```

### Response
```json
{
  "data": {
    "id": "db-123",
    "name": "updated-database-name",
    "engine": "postgresql",
    "version": "12.7",
    "status": "running",
    "host": "db-123.example.com",
    "port": 5432,
    "size": 15,
    "storage_type": "ssd",
    "created_at": "2023-04-01T12:00:00Z",
    "updated_at": "2023-04-20T10:45:00Z"
  }
}
```

## DELETE /databases/{id}
Delete a database instance.

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| id | string | The ID of the database instance. | Yes |

### Response
```json
{
  "data": {
    "id": "db-123",
    "name": "updated-database-name",
    "status": "deleting"
  }
}
```

### Error Codes
| Status Code | Description |
| --- | --- |
| 400 Bad Request | Invalid request parameters. |
| 404 Not Found | The specified database instance was not found. |
| 409 Conflict | The database instance is in a state that prevents the requested operation. |
| 500 Internal Server Error | An unexpected error occurred while processing the request. |