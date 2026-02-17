---
title: Configuration Management API
description: Manage system configurations and settings across your infrastructure.
keywords: [configuration, management, settings, infrastructure, api]
category: api-reference
---

## `GET /configurations`
Retrieve a list of all available configurations.

### Parameters
| Name | Type | Description |
| ---- | ---- | ----------- |
| `page` | `integer` | The page number to retrieve (default: 1) |
| `limit` | `integer` | The number of results to return per page (default: 20) |
| `search` | `string` | Search configurations by name or description |

### Response
```json
{
  "total": 100,
  "page": 1,
  "limit": 20,
  "data": [
    {
      "id": "config-001",
      "name": "Web Server Configuration",
      "description": "Configuration for web servers in the production environment",
      "environment": "production",
      "createdAt": "2023-04-01T12:00:00Z",
      "updatedAt": "2023-04-15T09:30:00Z"
    },
    {
      "id": "config-002",
      "name": "Database Configuration",
      "description": "Configuration for the main database cluster",
      "environment": "production",
      "createdAt": "2023-03-20T15:45:00Z",
      "updatedAt": "2023-04-10T11:20:00Z"
    }
  ]
}
```

## `GET /configurations/{id}`
Retrieve a specific configuration by ID.

### Parameters
| Name | Type | Description |
| ---- | ---- | ----------- |
| `id` | `string` | The ID of the configuration to retrieve |

### Response
```json
{
  "id": "config-001",
  "name": "Web Server Configuration",
  "description": "Configuration for web servers in the production environment",
  "environment": "production",
  "settings": {
    "webServerPort": 80,
    "maxConnections": 1000,
    "logLevel": "info"
  },
  "createdAt": "2023-04-01T12:00:00Z",
  "updatedAt": "2023-04-15T09:30:00Z"
}
```

## `POST /configurations`
Create a new configuration.

### Request Body
```json
{
  "name": "Application Configuration",
  "description": "Configuration for the main application",
  "environment": "staging",
  "settings": {
    "apiPort": 8080,
    "maxRequests": 500,
    "logLevel": "debug"
  }
}
```

### Response
```json
{
  "id": "config-003",
  "name": "Application Configuration",
  "description": "Configuration for the main application",
  "environment": "staging",
  "settings": {
    "apiPort": 8080,
    "maxRequests": 500,
    "logLevel": "debug"
  },
  "createdAt": "2023-04-20T14:22:00Z",
  "updatedAt": "2023-04-20T14:22:00Z"
}
```

## `PUT /configurations/{id}`
Update an existing configuration.

### Parameters
| Name | Type | Description |
| ---- | ---- | ----------- |
| `id` | `string` | The ID of the configuration to update |

### Request Body
```json
{
  "name": "Updated Web Server Configuration",
  "description": "Configuration for web servers in the production environment",
  "environment": "production",
  "settings": {
    "webServerPort": 80,
    "maxConnections": 2000,
    "logLevel": "info"
  }
}
```

### Response
```json
{
  "id": "config-001",
  "name": "Updated Web Server Configuration",
  "description": "Configuration for web servers in the production environment",
  "environment": "production",
  "settings": {
    "webServerPort": 80,
    "maxConnections": 2000,
    "logLevel": "info"
  },
  "createdAt": "2023-04-01T12:00:00Z",
  "updatedAt": "2023-04-20T16:45:00Z"
}
```

## `DELETE /configurations/{id}`
Delete a specific configuration by ID.

### Parameters
| Name | Type | Description |
| ---- | ---- | ----------- |
| `id` | `string` | The ID of the configuration to delete |

### Response
No content.

### Error Codes
| Status Code | Description |
| ----------- | ----------- |
| 404 Not Found | The specified configuration was not found. |
| 500 Internal Server Error | An unexpected error occurred while processing the request. |