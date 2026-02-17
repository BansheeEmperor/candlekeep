---
title: User Management API
description: API for managing user accounts and profiles
keywords:
  - user management
  - user accounts
  - user profiles
  - authentication
  - authorization
category: api-reference
---

## GET /users

Retrieve a list of users.

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| page | integer | No | The page number to retrieve (default: 1) |
| limit | integer | No | The number of results to return per page (default: 20) |
| search | string | No | Search query to filter users |

### Response

```json
{
  "total": 100,
  "page": 1,
  "limit": 20,
  "data": [
    {
      "id": "123456789",
      "name": "John Doe",
      "email": "john.doe@example.com",
      "createdAt": "2023-04-01T12:00:00Z",
      "updatedAt": "2023-04-01T12:00:00Z"
    },
    {
      "id": "987654321",
      "name": "Jane Smith",
      "email": "jane.smith@example.com",
      "createdAt": "2023-03-15T09:30:00Z",
      "updatedAt": "2023-03-20T14:45:00Z"
    }
  ]
}
```

### Error Codes

| Code | Description |
| --- | --- |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 500 | Internal Server Error |

## GET /users/{userId}

Retrieve a specific user by ID.

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| userId | string | Yes | The ID of the user to retrieve |

### Response

```json
{
  "id": "123456789",
  "name": "John Doe",
  "email": "john.doe@example.com",
  "createdAt": "2023-04-01T12:00:00Z",
  "updatedAt": "2023-04-01T12:00:00Z"
}
```

### Error Codes

| Code | Description |
| --- | --- |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 500 | Internal Server Error |

## POST /users

Create a new user.

### Request Body

```json
{
  "name": "John Doe",
  "email": "john.doe@example.com",
  "password": "mypassword123"
}
```

### Response

```json
{
  "id": "123456789",
  "name": "John Doe",
  "email": "john.doe@example.com",
  "createdAt": "2023-04-01T12:00:00Z",
  "updatedAt": "2023-04-01T12:00:00Z"
}
```

### Error Codes

| Code | Description |
| --- | --- |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 409 | Conflict (email already exists) |
| 500 | Internal Server Error |

## PATCH /users/{userId}

Update an existing user.

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| userId | string | Yes | The ID of the user to update |

### Request Body

```json
{
  "name": "John Doe Updated",
  "email": "john.doe.updated@example.com"
}
```

### Response

```json
{
  "id": "123456789",
  "name": "John Doe Updated",
  "email": "john.doe.updated@example.com",
  "createdAt": "2023-04-01T12:00:00Z",
  "updatedAt": "2023-04-02T15:30:00Z"
}
```

### Error Codes

| Code | Description |
| --- | --- |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 409 | Conflict (email already exists) |
| 500 | Internal Server Error |