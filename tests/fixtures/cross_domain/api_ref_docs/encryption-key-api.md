---
title: Encryption Key API
description: A RESTful API for managing encryption keys
keywords: [encryption, keys, security, cryptography, api]
category: api-reference
---

## GET /keys

Retrieve a list of encryption keys.

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| page | integer | No | The page number to retrieve (default: 1) |
| limit | integer | No | The number of results to return per page (default: 20) |

### Response

```json
{
  "data": [
    {
      "id": "123456789",
      "name": "Primary Key",
      "created_at": "2023-04-01T12:00:00Z",
      "updated_at": "2023-04-15T10:30:00Z"
    },
    {
      "id": "987654321",
      "name": "Backup Key",
      "created_at": "2023-03-15T08:45:00Z",
      "updated_at": "2023-04-10T14:20:00Z"
    }
  ],
  "meta": {
    "total": 25,
    "page": 1,
    "limit": 20
  }
}
```

### Error Codes

| Status Code | Description |
|-------------|-------------|
| 400 | Bad Request |
| 401 | Unauthorized |
| 500 | Internal Server Error |

## GET /keys/{id}

Retrieve a specific encryption key by ID.

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| id | string | Yes | The ID of the encryption key to retrieve |

### Response

```json
{
  "id": "123456789",
  "name": "Primary Key",
  "created_at": "2023-04-01T12:00:00Z",
  "updated_at": "2023-04-15T10:30:00Z"
}
```

### Error Codes

| Status Code | Description |
|-------------|-------------|
| 400 | Bad Request |
| 404 | Not Found |
| 500 | Internal Server Error |

## POST /keys

Create a new encryption key.

### Request Body

```json
{
  "name": "New Key"
}
```

### Response

```json
{
  "id": "987654321",
  "name": "New Key",
  "created_at": "2023-04-20T15:45:00Z",
  "updated_at": "2023-04-20T15:45:00Z"
}
```

### Error Codes

| Status Code | Description |
|-------------|-------------|
| 400 | Bad Request |
| 401 | Unauthorized |
| 500 | Internal Server Error |

## PUT /keys/{id}

Update an existing encryption key.

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| id | string | Yes | The ID of the encryption key to update |

### Request Body

```json
{
  "name": "Updated Key"
}
```

### Response

```json
{
  "id": "987654321",
  "name": "Updated Key",
  "created_at": "2023-04-20T15:45:00Z",
  "updated_at": "2023-04-21T09:15:00Z"
}
```

### Error Codes

| Status Code | Description |
|-------------|-------------|
| 400 | Bad Request |
| 404 | Not Found |
| 401 | Unauthorized |
| 500 | Internal Server Error |

## DELETE /keys/{id}

Delete an existing encryption key.

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| id | string | Yes | The ID of the encryption key to delete |

### Response

```json
{
  "message": "Encryption key deleted successfully"
}
```

### Error Codes

| Status Code | Description |
|-------------|-------------|
| 404 | Not Found |
| 401 | Unauthorized |
| 500 | Internal Server Error |