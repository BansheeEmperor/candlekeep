---
title: SSO Integration API
description: API for integrating single sign-on (SSO) authentication with your application.
keywords: [sso, authentication, oauth, saml, openid]
category: api-reference
---

## `POST /sso/login`

Authenticate a user and initiate a single sign-on session.

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `provider` | string | Yes | The SSO identity provider to use (e.g. "google", "azure", "okta"). |
| `redirect_uri` | string | Yes | The URI to redirect the user to after successful authentication. |

### Request Body

```json
{
  "provider": "google",
  "redirect_uri": "https://example.com/callback"
}
```

### Response

```json
{
  "session_token": "abc123def456ghi789",
  "user": {
    "id": "123456789",
    "name": "John Doe",
    "email": "john@example.com"
  }
}
```

### Error Codes

| Status Code | Description |
| --- | --- |
| 400 | Bad request (e.g. missing required parameters) |
| 401 | Authentication failed |
| 404 | Identity provider not found |
| 500 | Internal server error |

## `POST /sso/logout`

Log out the current user and invalidate their SSO session.

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `session_token` | string | Yes | The session token to invalidate. |

### Request Body

```json
{
  "session_token": "abc123def456ghi789"
}
```

### Response

```json
{
  "message": "Logout successful"
}
```

### Error Codes

| Status Code | Description |
| --- | --- |
| 400 | Bad request (e.g. missing required parameters) |
| 401 | Authentication failed |
| 404 | Session not found |
| 500 | Internal server error |

## `GET /sso/user`

Retrieve information about the currently authenticated user.

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `session_token` | string | Yes | The session token of the authenticated user. |

### Response

```json
{
  "user": {
    "id": "123456789",
    "name": "John Doe",
    "email": "john@example.com",
    "provider": "google"
  }
}
```

### Error Codes

| Status Code | Description |
| --- | --- |
| 400 | Bad request (e.g. missing required parameters) |
| 401 | Authentication failed |
| 404 | Session not found |
| 500 | Internal server error |

## `POST /sso/refresh`

Refresh an existing SSO session.

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `session_token` | string | Yes | The session token to refresh. |

### Request Body

```json
{
  "session_token": "abc123def456ghi789"
}
```

### Response

```json
{
  "session_token": "def456ghi789jkl012",
  "user": {
    "id": "123456789",
    "name": "John Doe",
    "email": "john@example.com"
  }
}
```

### Error Codes

| Status Code | Description |
| --- | --- |
| 400 | Bad request (e.g. missing required parameters) |
| 401 | Authentication failed |
| 404 | Session not found |
| 500 | Internal server error |