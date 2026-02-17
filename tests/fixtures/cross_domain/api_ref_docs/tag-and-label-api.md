---
title: Tag and Label API
description: API for managing tags and labels on resources
keywords: [tags, labels, resources, metadata, api]
category: api-reference
---

## Get All Tags
`GET /tags`

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| page | integer | Page number for pagination | No |
| per_page | integer | Number of results per page | No |
| search | string | Search tags by name | No |

### Response
```json
{
  "data": [
    {
      "id": "123",
      "name": "important",
      "description": "High priority tag",
      "color": "#FF0000",
      "created_at": "2023-04-01T12:00:00Z",
      "updated_at": "2023-04-02T10:30:00Z"
    },
    {
      "id": "456",
      "name": "frontend",
      "description": "Related to frontend development",
      "color": "#00FF00",
      "created_at": "2023-03-15T08:45:00Z",
      "updated_at": "2023-03-20T14:20:00Z"
    }
  ],
  "meta": {
    "total": 50,
    "page": 1,
    "per_page": 2
  }
}
```

## Get a Tag
`GET /tags/{id}`

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| id | string | ID of the tag | Yes |

### Response
```json
{
  "data": {
    "id": "123",
    "name": "important",
    "description": "High priority tag",
    "color": "#FF0000",
    "created_at": "2023-04-01T12:00:00Z",
    "updated_at": "2023-04-02T10:30:00Z"
  }
}
```

## Create a Tag
`POST /tags`

### Request Body
```json
{
  "name": "new-tag",
  "description": "This is a new tag",
  "color": "#0000FF"
}
```

### Response
```json
{
  "data": {
    "id": "789",
    "name": "new-tag",
    "description": "This is a new tag",
    "color": "#0000FF",
    "created_at": "2023-04-03T15:20:00Z",
    "updated_at": "2023-04-03T15:20:00Z"
  }
}
```

## Update a Tag
`PUT /tags/{id}`

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| id | string | ID of the tag | Yes |

### Request Body
```json
{
  "name": "updated-tag",
  "description": "This tag has been updated",
  "color": "#00FFFF"
}
```

### Response
```json
{
  "data": {
    "id": "789",
    "name": "updated-tag",
    "description": "This tag has been updated",
    "color": "#00FFFF",
    "created_at": "2023-04-03T15:20:00Z",
    "updated_at": "2023-04-04T09:45:00Z"
  }
}
```

## Delete a Tag
`DELETE /tags/{id}`

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| id | string | ID of the tag | Yes |

### Response
```json
{
  "data": {
    "id": "789",
    "name": "updated-tag",
    "description": "This tag has been updated",
    "color": "#00FFFF",
    "created_at": "2023-04-03T15:20:00Z",
    "updated_at": "2023-04-04T09:45:00Z",
    "deleted_at": "2023-04-05T11:30:00Z"
  }
}
```

## Error Codes
| Status Code | Description |
| --- | --- |
| 400 Bad Request | Invalid request data |
| 404 Not Found | Resource not found |
| 409 Conflict | Resource already exists |
| 500 Internal Server Error | Internal server error |