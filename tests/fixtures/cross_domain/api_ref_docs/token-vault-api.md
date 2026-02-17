---
title: Token Vault API
description: API for managing and securing access tokens
keywords: [token, vault, authentication, authorization, security]
category: api-reference
---

## Get Access Token

### GET /tokens/{token_id}

Retrieves an access token by its ID.

#### Parameters

| Name       | Type   | Required | Description                 |
|------------|--------|----------|----------------------------|
| `token_id` | string | true     | The unique identifier of the access token |

#### Response

```json
{
  "id": "abc123",
  "name": "Example Token",
  "type": "personal_access_token",
  "scopes": ["read:profile", "write:posts"],
  "created_at": "2023-04-01T12:00:00Z",
  "expires_at": "2024-04-01T12:00:00Z"
}
```

#### Error Codes

| Status Code | Description                          |
|-------------|--------------------------------------|
| 404         | Token not found                      |
| 500         | Internal server error                |

## List Access Tokens

### GET /tokens

Retrieves a list of access tokens.

#### Parameters

| Name       | Type   | Required | Description                 |
|------------|--------|----------|----------------------------|
| `page`     | integer| false    | The page number to retrieve |
| `per_page` | integer| false    | The number of results per page |

#### Response

```json
{
  "data": [
    {
      "id": "abc123",
      "name": "Example Token",
      "type": "personal_access_token",
      "scopes": ["read:profile", "write:posts"],
      "created_at": "2023-04-01T12:00:00Z",
      "expires_at": "2024-04-01T12:00:00Z"
    },
    {
      "id": "def456",
      "name": "Another Token",
      "type": "api_key",
      "scopes": ["read:data", "write:data"],
      "created_at": "2023-03-15T09:30:00Z",
      "expires_at": "2024-03-15T09:30:00Z"
    }
  ],
  "meta": {
    "total_count": 50,
    "total_pages": 5,
    "current_page": 1
  }
}
```

#### Error Codes

| Status Code | Description                          |
|-------------|--------------------------------------|
| 500         | Internal server error                |

## Create Access Token

### POST /tokens

Creates a new access token.

#### Request Body

```json
{
  "name": "Example Token",
  "type": "personal_access_token",
  "scopes": ["read:profile", "write:posts"],
  "expires_at": "2024-04-01T12:00:00Z"
}
```

#### Response

```json
{
  "id": "abc123",
  "name": "Example Token",
  "type": "personal_access_token",
  "scopes": ["read:profile", "write:posts"],
  "created_at": "2023-04-01T12:00:00Z",
  "expires_at": "2024-04-01T12:00:00Z"
}
```

#### Error Codes

| Status Code | Description                          |
|-------------|--------------------------------------|
| 400         | Invalid request body                 |
| 500         | Internal server error                |

## Revoke Access Token

### DELETE /tokens/{token_id}

Revokes an access token by its ID.

#### Parameters

| Name       | Type   | Required | Description                 |
|------------|--------|----------|----------------------------|
| `token_id` | string | true     | The unique identifier of the access token |

#### Response

```json
{
  "message": "Token revoked successfully"
}
```

#### Error Codes

| Status Code | Description                          |
|-------------|--------------------------------------|
| 404         | Token not found                      |
| 500         | Internal server error                |