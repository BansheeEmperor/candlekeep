---
title: Resource Tagging API
description: Manage tags for resources in your application.
keywords: [tags, resources, metadata, api, rest]
category: api-reference
---

## Get Tags

`GET /tags`

### Parameters

| Name | Type | Description |
| --- | --- | --- |
| `resource_id` | string | (Optional) Filter tags by resource ID. |
| `tag_name` | string | (Optional) Filter tags by name. |
| `page` | integer | (Optional) Page number for pagination. Default is 1. |
| `per_page` | integer | (Optional) Number of results per page. Default is 20, max is 100. |

### Response

```json
{
  "data": [
    {
      "id": "123",
      "resource_id": "abc123",
      "name": "production",
      "created_at": "2023-04-01T12:00:00Z",
      "updated_at": "2023-04-01T12:00:00Z"
    },
    {
      "id": "456",
      "resource_id": "abc123",
      "name": "frontend",
      "created_at": "2023-04-02T10:30:00Z",
      "updated_at": "2023-04-02T10:30:00Z"
    }
  ],
  "meta": {
    "total": 2,
    "page": 1,
    "per_page": 20
  }
}
```

## Create Tag

`POST /tags`

### Request Body

```json
{
  "resource_id": "abc123",
  "name": "production"
}
```

### Response

```json
{
  "id": "123",
  "resource_id": "abc123",
  "name": "production",
  "created_at": "2023-04-01T12:00:00Z",
  "updated_at": "2023-04-01T12:00:00Z"
}
```

## Update Tag

`PUT /tags/{id}`

### Parameters

| Name | Type | Description |
| --- | --- | --- |
| `id` | string | ID of the tag to update. |

### Request Body

```json
{
  "name": "staging"
}
```

### Response

```json
{
  "id": "123",
  "resource_id": "abc123",
  "name": "staging",
  "created_at": "2023-04-01T12:00:00Z",
  "updated_at": "2023-04-02T15:30:00Z"
}
```

## Delete Tag

`DELETE /tags/{id}`

### Parameters

| Name | Type | Description |
| --- | --- | --- |
| `id` | string | ID of the tag to delete. |

### Response

```json
{
  "message": "Tag deleted successfully."
}
```

## Error Codes

| Status Code | Description |
| --- | --- |
| 400 Bad Request | Invalid request parameters. |
| 404 Not Found | Requested resource not found. |
| 409 Conflict | Tag already exists for the given resource. |
| 500 Internal Server Error | An unexpected error occurred. |