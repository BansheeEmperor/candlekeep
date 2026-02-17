---
title: Container Registry API
description: API for managing private container image registries
keywords: [container, registry, docker, image, repository, tag]
category: api-reference
---

## List Repositories

`GET /v2/repositories`

### Parameters

| Name | Type | Description |
| --- | --- | --- |
| `namespace` | string | (optional) Filter repositories by namespace |
| `name` | string | (optional) Filter repositories by name |
| `page` | integer | (optional) Page number for pagination |
| `per_page` | integer | (optional) Number of results per page (default: 25, max: 100) |

### Response

```json
{
  "total_count": 10,
  "repositories": [
    {
      "namespace": "myorg",
      "name": "my-app",
      "tags_count": 3
    },
    {
      "namespace": "myorg",
      "name": "another-app",
      "tags_count": 2
    }
  ]
}
```

### Error Codes

| Code | Description |
| --- | --- |
| 400 | Invalid parameters |
| 401 | Unauthorized |
| 500 | Internal server error |

## Get Repository Details

`GET /v2/repositories/{namespace}/{name}`

### Parameters

| Name | Type | Description |
| --- | --- | --- |
| `namespace` | string | The namespace of the repository |
| `name` | string | The name of the repository |

### Response

```json
{
  "namespace": "myorg",
  "name": "my-app",
  "created_at": "2023-04-01T12:34:56Z",
  "updated_at": "2023-04-15T09:12:34Z",
  "tags_count": 3
}
```

### Error Codes

| Code | Description |
| --- | --- |
| 404 | Repository not found |
| 401 | Unauthorized |
| 500 | Internal server error |

## List Repository Tags

`GET /v2/repositories/{namespace}/{name}/tags`

### Parameters

| Name | Type | Description |
| --- | --- | --- |
| `namespace` | string | The namespace of the repository |
| `name` | string | The name of the repository |
| `page` | integer | (optional) Page number for pagination |
| `per_page` | integer | (optional) Number of results per page (default: 25, max: 100) |

### Response

```json
{
  "total_count": 3,
  "tags": [
    {
      "name": "v1.0.0",
      "created_at": "2023-04-01T12:34:56Z"
    },
    {
      "name": "v1.0.1",
      "created_at": "2023-04-08T15:20:00Z"
    },
    {
      "name": "latest",
      "created_at": "2023-04-15T09:12:34Z"
    }
  ]
}
```

### Error Codes

| Code | Description |
| --- | --- |
| 404 | Repository not found |
| 401 | Unauthorized |
| 500 | Internal server error |

## Push Image

`POST /v2/repositories/{namespace}/{name}/tags/{tag}`

### Request Body

```json
{
  "image_data": "base64_encoded_image_data"
}
```

### Response

```json
{
  "tag": "v1.0.0",
  "digest": "sha256:abc123def456ghi789jkl012mno345pqr678stu901vwx",
  "size": 123456789,
  "uploaded_at": "2023-04-01T12:34:56Z"
}
```

### Error Codes

| Code | Description |
| --- | --- |
| 404 | Repository not found |
| 401 | Unauthorized |
| 400 | Invalid request body |
| 413 | Image size too large |
| 500 | Internal server error |

## Delete Image Tag

`DELETE /v2/repositories/{namespace}/{name}/tags/{tag}`

### Parameters

| Name | Type | Description |
| --- | --- | --- |
| `namespace` | string | The namespace of the repository |
| `name` | string | The name of the repository |
| `tag` | string | The tag of the image to delete |

### Response

```json
{
  "message": "Image tag deleted"
}
```

### Error Codes

| Code | Description |
| --- | --- |
| 404 | Repository or tag not found |
| 401 | Unauthorized |
| 500 | Internal server error |