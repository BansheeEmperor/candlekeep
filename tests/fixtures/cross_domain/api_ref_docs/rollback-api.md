---
title: Rollback API
description: Rollback data to a previous state
keywords: 
  - rollback
  - data
  - version control
  - revert
  - restore
category: api-reference
---

## GET /rollbacks

Retrieve a list of available rollback points.

### Parameters

| Name | Type | Required | Description |
| ---- | ---- | -------- | ----------- |
| limit | integer | No | Maximum number of rollbacks to return |
| offset | integer | No | Offset to start returning rollbacks from |

### Response

```json
[
  {
    "id": "123abc",
    "timestamp": "2023-04-01T12:34:56Z",
    "comment": "Rolled back to fix bug #1234"
  },
  {
    "id": "456def",
    "timestamp": "2023-03-15T09:00:00Z",
    "comment": "Rollback before major update"
  }
]
```

## POST /rollbacks

Create a new rollback point.

### Request Body

```json
{
  "comment": "Rollback before major update"
}
```

### Response

```json
{
  "id": "789ghi",
  "timestamp": "2023-04-05T15:30:00Z",
  "comment": "Rollback before major update"
}
```

## GET /rollbacks/{id}

Retrieve details of a specific rollback point.

### Parameters

| Name | Type | Required | Description |
| ---- | ---- | -------- | ----------- |
| id | string | Yes | ID of the rollback point |

### Response

```json
{
  "id": "123abc",
  "timestamp": "2023-04-01T12:34:56Z",
  "comment": "Rolled back to fix bug #1234"
}
```

## POST /rollbacks/{id}/restore

Restore the data to the specified rollback point.

### Parameters

| Name | Type | Required | Description |
| ---- | ---- | -------- | ----------- |
| id | string | Yes | ID of the rollback point |

### Response

```json
{
  "status": "success",
  "message": "Data has been restored to the specified rollback point."
}
```

## DELETE /rollbacks/{id}

Delete a specific rollback point.

### Parameters

| Name | Type | Required | Description |
| ---- | ---- | -------- | ----------- |
| id | string | Yes | ID of the rollback point |

### Response

```json
{
  "status": "success",
  "message": "Rollback point has been deleted."
}
```

### Error Codes

| Status Code | Description |
| ----------- | ----------- |
| 400 | Bad Request - Invalid request parameters |
| 404 | Not Found - Rollback point not found |
| 500 | Internal Server Error - An unexpected error occurred |