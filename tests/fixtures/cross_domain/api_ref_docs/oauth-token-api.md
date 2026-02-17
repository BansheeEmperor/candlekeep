---
title: OAuth Token API
description: Manage OAuth 2.0 access tokens for your application.
keywords: [oauth, token, authentication, authorization, api]
category: api-reference
---

## Obtain Access Token

### POST /oauth/token

Obtain an OAuth 2.0 access token using the client credentials grant type.

#### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| grant_type | string | Yes | The grant type, must be `client_credentials`. |
| client_id | string | Yes | Your application's client ID. |
| client_secret | string | Yes | Your application's client secret. |

#### Request Body

```json
{
  "grant_type": "client_credentials",
  "client_id": "your_client_id",
  "client_secret": "your_client_secret"
}
```

#### Response

```json
{
  "access_token": "abcd1234efgh5678",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

#### Error Codes

| Status Code | Error | Description |
| --- | --- | --- |
| 400 | `invalid_request` | The request is missing a required parameter, includes an unsupported parameter value, or is otherwise malformed. |
| 401 | `invalid_client` | Client authentication failed (e.g., unknown client, no client authentication included, or unsupported authentication method). |
| 500 | `server_error` | The authorization server encountered an unexpected condition that prevented it from fulfilling the request. |

## Refresh Access Token

### POST /oauth/token

Obtain a new access token using a valid refresh token.

#### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| grant_type | string | Yes | The grant type, must be `refresh_token`. |
| refresh_token | string | Yes | A valid refresh token. |
| client_id | string | Yes | Your application's client ID. |
| client_secret | string | Yes | Your application's client secret. |

#### Request Body

```json
{
  "grant_type": "refresh_token",
  "refresh_token": "abcd1234efgh5678",
  "client_id": "your_client_id",
  "client_secret": "your_client_secret"
}
```

#### Response

```json
{
  "access_token": "new_abcd1234efgh5678",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "new_refresh_token"
}
```

#### Error Codes

| Status Code | Error | Description |
| --- | --- | --- |
| 400 | `invalid_request` | The request is missing a required parameter, includes an unsupported parameter value, or is otherwise malformed. |
| 401 | `invalid_client` | Client authentication failed (e.g., unknown client, no client authentication included, or unsupported authentication method). |
| 401 | `invalid_grant` | The provided authorization grant (e.g., authorization code, resource owner credentials) or refresh token is invalid, expired, revoked, does not match the redirection URI used in the authorization request, or was issued to another client. |
| 500 | `server_error` | The authorization server encountered an unexpected condition that prevented it from fulfilling the request. |

## Revoke Access Token

### POST /oauth/revoke

Revoke an existing access token or refresh token.

#### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| token | string | Yes | The token to be revoked (access token or refresh token). |
| client_id | string | Yes | Your application's client ID. |
| client_secret | string | Yes | Your application's client secret. |

#### Request Body

```json
{
  "token": "abcd1234efgh5678",
  "client_id": "your_client_id",
  "client_secret": "your_client_secret"
}
```

#### Response

```json
{
  "status": "ok"
}
```

#### Error Codes

| Status Code | Error | Description |
| --- | --- | --- |
| 400 | `invalid_request` | The request is missing a required parameter, includes an unsupported parameter value, or is otherwise malformed. |
| 401 | `invalid_client` | Client authentication failed (e.g., unknown client, no client authentication included, or unsupported authentication method). |
| 500 | `server_error` | The authorization server encountered an unexpected condition that prevented it from fulfilling the request. |

## Validate Access Token

### POST /oauth/introspect

Check the validity of an access token.

#### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| token | string | Yes | The access token to be validated. |
| client_id | string | Yes | Your application's client ID. |
| client_secret | string | Yes | Your application's client secret. |

#### Request Body

```json
{
  "token": "abcd1234efgh5678",
  "client_id": "your_client_id",
  "client_secret": "your_client_secret"
}
```

#### Response

```json
{
  "active": true,
  "client_id": "your_client_id",
  "token_type": "Bearer",
  "exp": 1621123456,
  "iat": 1621123156,
  "scope": "read write"
}
```

#### Error Codes

| Status Code | Error | Description |
| --- | --- | --- |
| 400 | `invalid_request` | The request is missing a required parameter, includes an unsupported parameter value, or is otherwise malformed. |
| 401 | `invalid_client` | Client authentication failed (e.g., unknown client, no client authentication included, or unsupported authentication method). |
| 500 | `server_error` | The authorization server encountered an unexpected condition that prevented it from fulfilling the request. |