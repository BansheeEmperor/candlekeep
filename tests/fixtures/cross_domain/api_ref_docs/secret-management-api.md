---
title: Secret Management API
description: Securely store and retrieve sensitive data for your application.
keywords: [secrets, encryption, security, key management, API]
category: api-reference
---

## GET /secrets

Retrieve a secret by its unique identifier.

### Parameters

| Name | Type | Description | Required |
| --- | --- | --- | --- |
| id | string | The unique identifier of the secret. | Yes |

### Response

```json
{
  "id": "abc123",
  "name": "API Key",
  "value": "s3cret_v@lue",
  "created_at": "2023-04-01T12:00:00Z",
  "updated_at": "2023-04-15T09:30:00Z"
}
```

### Error Codes

| Code | Description |
| --- | --- |
| 404 | Secret not found |

## POST /secrets

Create a new secret.

### Request Body

```json
{
  "name": "API Key",
  "value": "s3cret_v@lue"
}
```

### Response

```json
{
  "id": "abc123",
  "name": "API Key",
  "value": "s3cret_v@lue",
  "created_at": "2023-04-01T12:00:00Z",
  "updated_at": "2023-04-01T12:00:00Z"
}
```

### Error Codes

| Code | Description |
| --- | --- |
| 400 | Invalid request body |

## PUT /secrets/{id}

Update an existing secret.

### Parameters

| Name | Type | Description | Required |
| --- | --- | --- | --- |
| id | string | The unique identifier of the secret. | Yes |

### Request Body

```json
{
  "name": "New API Key",
  "value": "new_s3cret_v@lue"
}
```

### Response

```json
{
  "id": "abc123",
  "name": "New API Key",
  "value": "new_s3cret_v@lue",
  "created_at": "2023-04-01T12:00:00Z",
  "updated_at": "2023-04-15T09:30:00Z"
}
```

### Error Codes

| Code | Description |
| --- | --- |
| 404 | Secret not found |
| 400 | Invalid request body |

## DELETE /secrets/{id}

Delete a secret by its unique identifier.

### Parameters

| Name | Type | Description | Required |
| --- | --- | --- | --- |
| id | string | The unique identifier of the secret. | Yes |

### Response

```json
{
  "message": "Secret deleted"
}
```

### Error Codes

| Code | Description |
| --- | --- |
| 404 | Secret not found |