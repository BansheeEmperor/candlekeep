---
title: Data Export API
description: API for exporting data from our platform
keywords: [data, export, reporting, analytics, csv, json]
category: api-reference
---

## GET /api/v1/data_exports

Retrieve a list of all available data exports.

### Parameters

| Name | Type | Description |
| --- | --- | --- |
| `limit` | integer | Maximum number of results to return (default: 25, max: 100) |
| `offset` | integer | Number of results to skip (default: 0) |
| `sort` | string | Field to sort by (e.g., `created_at`, `name`) |
| `order` | string | Sort order (`asc` or `desc`) |

### Response

```json
{
  "data": [
    {
      "id": "123",
      "name": "Monthly Sales Report",
      "description": "Export of monthly sales data",
      "created_at": "2023-04-01T12:00:00Z",
      "updated_at": "2023-04-01T12:00:00Z",
      "file_type": "csv",
      "status": "completed"
    },
    {
      "id": "456",
      "name": "Customer List",
      "description": "Export of all customer data",
      "created_at": "2023-03-15T09:30:00Z",
      "updated_at": "2023-03-15T09:30:00Z",
      "file_type": "json",
      "status": "pending"
    }
  ],
  "meta": {
    "total_count": 2,
    "limit": 25,
    "offset": 0
  }
}
```

## POST /api/v1/data_exports

Create a new data export.

### Request Body

```json
{
  "name": "Quarterly Revenue Report",
  "description": "Export of quarterly revenue data",
  "file_type": "csv",
  "filters": {
    "start_date": "2023-01-01",
    "end_date": "2023-03-31"
  }
}
```

### Response

```json
{
  "id": "789",
  "name": "Quarterly Revenue Report",
  "description": "Export of quarterly revenue data",
  "created_at": "2023-04-01T15:30:00Z",
  "updated_at": "2023-04-01T15:30:00Z",
  "file_type": "csv",
  "status": "pending"
}
```

## GET /api/v1/data_exports/{id}

Retrieve details of a specific data export.

### Parameters

| Name | Type | Description |
| --- | --- | --- |
| `id` | string | ID of the data export |

### Response

```json
{
  "id": "123",
  "name": "Monthly Sales Report",
  "description": "Export of monthly sales data",
  "created_at": "2023-04-01T12:00:00Z",
  "updated_at": "2023-04-01T12:00:00Z",
  "file_type": "csv",
  "status": "completed",
  "download_url": "https://example.com/data_exports/123.csv"
}
```

## DELETE /api/v1/data_exports/{id}

Cancel a pending data export.

### Parameters

| Name | Type | Description |
| --- | --- | --- |
| `id` | string | ID of the data export |

### Response

```json
{
  "id": "456",
  "name": "Customer List",
  "description": "Export of all customer data",
  "created_at": "2023-03-15T09:30:00Z",
  "updated_at": "2023-03-15T09:30:00Z",
  "file_type": "json",
  "status": "cancelled"
}
```

## Error Codes

| Status Code | Description |
| --- | --- |
| 400 Bad Request | Invalid request parameters |
| 401 Unauthorized | Authentication credentials are missing or incorrect |
| 403 Forbidden | User does not have permission to perform this action |
| 404 Not Found | Requested resource not found |
| 500 Internal Server Error | An unexpected error occurred on the server |