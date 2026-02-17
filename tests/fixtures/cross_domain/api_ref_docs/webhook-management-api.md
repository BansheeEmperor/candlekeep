---
title: Webhook Management API
description: Manage webhooks for your application
keywords: [webhooks, integration, events, notifications, automation]
category: api-reference
---

## Create Webhook

`POST /webhooks`

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `url` | string | Yes | The URL to receive webhook notifications |
| `events` | array[string] | Yes | A list of event types to subscribe to |
| `secret` | string | No | A secret key used to sign webhook payloads |

### Request Body

```json
{
  "url": "https://example.com/webhook",
  "events": ["user.created", "user.updated", "order.placed"],
  "secret": "abc123def456"
}
```

### Response

```json
{
  "id": "webhook_123456789",
  "url": "https://example.com/webhook",
  "events": ["user.created", "user.updated", "order.placed"],
  "secret": "abc123def456",
  "created_at": "2023-04-01T12:00:00Z"
}
```

### Error Codes

| Code | Description |
| --- | --- |
| 400 | Invalid request body |
| 409 | Webhook with the same URL already exists |

## List Webhooks

`GET /webhooks`

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `page` | integer | No | The page number to retrieve (default: 1) |
| `per_page` | integer | No | The number of results per page (default: 20, max: 100) |

### Response

```json
{
  "data": [
    {
      "id": "webhook_123456789",
      "url": "https://example.com/webhook",
      "events": ["user.created", "user.updated", "order.placed"],
      "secret": "abc123def456",
      "created_at": "2023-04-01T12:00:00Z"
    },
    {
      "id": "webhook_987654321",
      "url": "https://example.com/another-webhook",
      "events": ["order.placed", "order.shipped"],
      "secret": "ghi789jkl012",
      "created_at": "2023-03-15T09:30:00Z"
    }
  ],
  "pagination": {
    "current_page": 1,
    "per_page": 20,
    "total_pages": 2,
    "total_count": 25
  }
}
```

### Error Codes

| Code | Description |
| --- | --- |
| 400 | Invalid request parameters |

## Retrieve Webhook

`GET /webhooks/{id}`

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | string | Yes | The ID of the webhook to retrieve |

### Response

```json
{
  "id": "webhook_123456789",
  "url": "https://example.com/webhook",
  "events": ["user.created", "user.updated", "order.placed"],
  "secret": "abc123def456",
  "created_at": "2023-04-01T12:00:00Z"
}
```

### Error Codes

| Code | Description |
| --- | --- |
| 404 | Webhook not found |

## Update Webhook

`PATCH /webhooks/{id}`

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | string | Yes | The ID of the webhook to update |

### Request Body

```json
{
  "url": "https://example.com/new-webhook",
  "events": ["user.created", "user.deleted", "order.placed"]
}
```

### Response

```json
{
  "id": "webhook_123456789",
  "url": "https://example.com/new-webhook",
  "events": ["user.created", "user.deleted", "order.placed"],
  "secret": "abc123def456",
  "created_at": "2023-04-01T12:00:00Z"
}
```

### Error Codes

| Code | Description |
| --- | --- |
| 404 | Webhook not found |
| 400 | Invalid request body |

## Delete Webhook

`DELETE /webhooks/{id}`

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | string | Yes | The ID of the webhook to delete |

### Response

```json
{
  "message": "Webhook deleted successfully"
}
```

### Error Codes

| Code | Description |
| --- | --- |
| 404 | Webhook not found |