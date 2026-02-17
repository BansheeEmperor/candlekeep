---
title: Migration and Import API
description: Programmatically migrate and import data into your application.
keywords: [migration, import, data, api, rest]
category: api-reference
---

## GET /migrations

Retrieve a list of all data migrations performed.

### Parameters

| Name | Type | Description |
| --- | --- | --- |
| `page` | integer | The page number to retrieve. Default is 1. |
| `per_page` | integer | The number of results to return per page. Default is 20, max is 100. |
| `status` | string | Filter by migration status (e.g., `pending`, `in_progress`, `completed`, `failed`). |

### Response

```json
{
  "data": [
    {
      "id": "abc123",
      "status": "completed",
      "source": "legacy_database",
      "target": "new_application",
      "created_at": "2023-04-01T12:00:00Z",
      "updated_at": "2023-04-01T12:05:00Z"
    },
    {
      "id": "def456",
      "status": "in_progress",
      "source": "csv_file",
      "target": "new_application",
      "created_at": "2023-04-02T09:30:00Z",
      "updated_at": "2023-04-02T10:15:00Z"
    }
  ],
  "meta": {
    "total": 50,
    "page": 1,
    "per_page": 20
  }
}
```

## POST /migrations

Create a new data migration.

### Request Body

```json
{
  "source": "legacy_database",
  "target": "new_application",
  "options": {
    "include_tables": ["users", "orders"],
    "exclude_tables": ["logs"]
  }
}
```

### Response

```json
{
  "id": "abc123",
  "status": "pending",
  "source": "legacy_database",
  "target": "new_application",
  "options": {
    "include_tables": ["users", "orders"],
    "exclude_tables": ["logs"]
  },
  "created_at": "2023-04-01T12:00:00Z",
  "updated_at": "2023-04-01T12:00:00Z"
}
```

## GET /migrations/{id}

Retrieve details of a specific data migration.

### Parameters

| Name | Type | Description |
| --- | --- | --- |
| `id` | string | The ID of the migration to retrieve. |

### Response

```json
{
  "id": "abc123",
  "status": "completed",
  "source": "legacy_database",
  "target": "new_application",
  "options": {
    "include_tables": ["users", "orders"],
    "exclude_tables": ["logs"]
  },
  "created_at": "2023-04-01T12:00:00Z",
  "updated_at": "2023-04-01T12:05:00Z",
  "logs": [
    {
      "level": "info",
      "message": "Migrating users table",
      "timestamp": "2023-04-01T12:00:10Z"
    },
    {
      "level": "error",
      "message": "Failed to migrate logs table",
      "timestamp": "2023-04-01T12:01:30Z"
    }
  ]
}
```

## POST /imports

Create a new data import.

### Request Body

```json
{
  "source": "csv_file",
  "target": "new_application",
  "options": {
    "file_path": "/uploads/data.csv",
    "mapping": {
      "name": "full_name",
      "email": "email_address",
      "created_at": "signup_date"
    }
  }
}
```

### Response

```json
{
  "id": "def456",
  "status": "pending",
  "source": "csv_file",
  "target": "new_application",
  "options": {
    "file_path": "/uploads/data.csv",
    "mapping": {
      "name": "full_name",
      "email": "email_address",
      "created_at": "signup_date"
    }
  },
  "created_at": "2023-04-02T09:30:00Z",
  "updated_at": "2023-04-02T09:30:00Z"
}
```

## Error Codes

| Status Code | Description |
| --- | --- |
| 400 Bad Request | The request was malformed or contained invalid data. |
| 401 Unauthorized | The request did not include valid authentication credentials. |
| 404 Not Found | The requested resource was not found. |
| 500 Internal Server Error | An unexpected error occurred on the server. |