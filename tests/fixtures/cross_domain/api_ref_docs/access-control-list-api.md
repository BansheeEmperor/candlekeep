---
title: Access Control List API
description: Manage access control lists for your application
keywords: [access-control, permissions, roles, authentication, authorization]
category: api-reference
---

## List ACLs
`GET /acls`

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| `page` | integer | The page number to retrieve | No |
| `limit` | integer | The number of results per page | No |

### Response
```json
{
  "data": [
    {
      "id": "acl-123",
      "name": "Admin ACL",
      "description": "Full access to all resources",
      "permissions": ["read:all", "write:all", "delete:all"]
    },
    {
      "id": "acl-456",
      "name": "Read-Only ACL", 
      "description": "Read-only access to all resources",
      "permissions": ["read:all"]
    }
  ],
  "pagination": {
    "currentPage": 1,
    "totalPages": 3,
    "totalResults": 6
  }
}
```

## Create ACL
`POST /acls`

### Request Body
```json
{
  "name": "Editor ACL",
  "description": "Read and write access to all resources",
  "permissions": ["read:all", "write:all"]
}
```

### Response
```json
{
  "id": "acl-789",
  "name": "Editor ACL",
  "description": "Read and write access to all resources",
  "permissions": ["read:all", "write:all"]
}
```

## Get ACL
`GET /acls/{id}`

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| `id` | string | The ID of the ACL to retrieve | Yes |

### Response
```json
{
  "id": "acl-123",
  "name": "Admin ACL",
  "description": "Full access to all resources",
  "permissions": ["read:all", "write:all", "delete:all"]
}
```

## Update ACL
`PUT /acls/{id}`

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| `id` | string | The ID of the ACL to update | Yes |

### Request Body
```json
{
  "name": "Admin ACL",
  "description": "Full access to all resources, except delete",
  "permissions": ["read:all", "write:all"]
}
```

### Response
```json
{
  "id": "acl-123",
  "name": "Admin ACL",
  "description": "Full access to all resources, except delete",
  "permissions": ["read:all", "write:all"]
}
```

## Delete ACL
`DELETE /acls/{id}`

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| `id` | string | The ID of the ACL to delete | Yes |

### Response
```json
{
  "message": "ACL deleted successfully"
}
```

## Error Codes
| Code | Description |
| --- | --- |
| 400 | Bad Request - Invalid request data |
| 401 | Unauthorized - Missing or invalid authentication credentials |
| 403 | Forbidden - Insufficient permissions to perform the requested action |
| 404 | Not Found - The requested resource was not found |
| 500 | Internal Server Error - An unexpected error occurred on the server |