---
title: Session Management API
description: API for managing user sessions and authentication
keywords: [session, authentication, login, logout, tokens]
category: api-reference
---

## POST /login
Authenticate a user and create a new session.

### Parameters
| Name | Type | Description |
| --- | --- | --- |
| username | string | The user's username |
| password | string | The user's password |

### Request Body
```json
{
  "username": "johndoe",
  "password": "mypassword"
}
```

### Response
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiI1ZTc0NjIwZTk4NTY3ODAwMTVjZWE1NzQiLCJleHAiOjE1ODQ3NjE2MDB9.XBe4gwDQW9mrgkdiQlwaYAhEXE5u6EU6UxBl62TPnx4",
  "expiresIn": 3600
}
```

### Error Codes
- `401 Unauthorized`: Invalid username or password

## POST /logout
Invalidate the current user's session.

### Request Body
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiI1ZTc0NjIwZTk4NTY3ODAwMTVjZWE1NzQiLCJleHAiOjE1ODQ3NjE2MDB9.XBe4gwDQW9mrgkdiQlwaYAhEXE5u6EU6UxBl62TPnx4"
}
```

### Response
```json
{
  "message": "Logout successful"
}
```

### Error Codes
- `401 Unauthorized`: Invalid or expired token

## GET /sessions
Retrieve a list of the current user's active sessions.

### Parameters
| Name | Type | Description |
| --- | --- | --- |
| token | string | The user's authentication token |

### Response
```json
[
  {
    "id": "5e74620e98567800015cea574",
    "createdAt": "2020-03-27T12:00:00Z",
    "expiresAt": "2020-03-27T13:00:00Z",
    "ipAddress": "192.168.1.100",
    "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.132 Safari/537.36"
  },
  {
    "id": "5e74620e98567800015cea575",
    "createdAt": "2020-03-26T15:30:00Z",
    "expiresAt": "2020-03-26T16:30:00Z",
    "ipAddress": "192.168.1.101",
    "userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.5 Safari/605.1.15"
  }
]
```

### Error Codes
- `401 Unauthorized`: Invalid or expired token

## DELETE /sessions/{id}
Invalidate a specific user session.

### Parameters
| Name | Type | Description |
| --- | --- | --- |
| id | string | The ID of the session to invalidate |
| token | string | The user's authentication token |

### Response
```json
{
  "message": "Session invalidated"
}
```

### Error Codes
- `401 Unauthorized`: Invalid or expired token
- `404 Not Found`: Session not found

## GET /me
Retrieve information about the current user.

### Parameters
| Name | Type | Description |
| --- | --- | --- |
| token | string | The user's authentication token |

### Response
```json
{
  "id": "5e74620e98567800015cea574",
  "username": "johndoe",
  "email": "johndoe@example.com",
  "createdAt": "2020-03-01T10:00:00Z",
  "updatedAt": "2020-03-15T14:30:00Z"
}
```

### Error Codes
- `401 Unauthorized`: Invalid or expired token