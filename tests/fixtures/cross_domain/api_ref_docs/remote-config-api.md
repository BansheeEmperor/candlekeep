---
title: Remote Config API
description: API for managing remote configuration settings for your application.
keywords: [remote config, configuration, settings, application]
category: api-reference
---

## GET /config

Retrieves the current remote configuration settings.

### Parameters

| Name | Type | Description |
| --- | --- | --- |
| `environment` | `string` | (Required) The environment to retrieve the configuration for (e.g. "production", "staging"). |

### Response

```json
{
  "settings": {
    "featureFlags": {
      "newUserOnboarding": true,
      "darkMode": false
    },
    "apiEndpoints": {
      "usersApi": "https://api.example.com/users",
      "ordersApi": "https://api.example.com/orders"
    },
    "appConfig": {
      "maxUploadSize": 10485760,
      "defaultPageSize": 25
    }
  }
}
```

### Error Codes

| Status Code | Description |
| --- | --- |
| 400 | Invalid `environment` parameter. |
| 404 | Configuration not found for the specified environment. |
| 500 | Internal server error. |

## POST /config

Creates or updates a remote configuration.

### Parameters

| Name | Type | Description |
| --- | --- | --- |
| `environment` | `string` | (Required) The environment to update the configuration for (e.g. "production", "staging"). |

### Request Body

```json
{
  "settings": {
    "featureFlags": {
      "newUserOnboarding": true,
      "darkMode": true
    },
    "apiEndpoints": {
      "usersApi": "https://api.example.com/users",
      "ordersApi": "https://api.example.com/orders"
    },
    "appConfig": {
      "maxUploadSize": 10485760,
      "defaultPageSize": 50
    }
  }
}
```

### Response

```json
{
  "message": "Configuration updated successfully."
}
```

### Error Codes

| Status Code | Description |
| --- | --- |
| 400 | Invalid `environment` parameter or request body. |
| 409 | Configuration already exists for the specified environment. |
| 500 | Internal server error. |

## GET /config/history

Retrieves the history of changes made to the remote configuration.

### Parameters

| Name | Type | Description |
| --- | --- | --- |
| `environment` | `string` | (Required) The environment to retrieve the configuration history for (e.g. "production", "staging"). |
| `limit` | `integer` | (Optional) The maximum number of changes to retrieve (default is 10). |
| `offset` | `integer` | (Optional) The number of changes to skip (used for pagination). |

### Response

```json
{
  "changes": [
    {
      "id": "c7d3b2a0-1234-5678-abcd-ef0123456789",
      "environment": "production",
      "updatedAt": "2023-04-15T12:34:56Z",
      "settings": {
        "featureFlags": {
          "newUserOnboarding": true,
          "darkMode": false
        },
        "apiEndpoints": {
          "usersApi": "https://api.example.com/users",
          "ordersApi": "https://api.example.com/orders"
        },
        "appConfig": {
          "maxUploadSize": 10485760,
          "defaultPageSize": 25
        }
      }
    },
    {
      "id": "d9e8c7b6-5432-1098-fedc-ba0987654321",
      "environment": "production",
      "updatedAt": "2023-04-14T09:45:12Z",
      "settings": {
        "featureFlags": {
          "newUserOnboarding": true,
          "darkMode": false
        },
        "apiEndpoints": {
          "usersApi": "https://api.example.com/users",
          "ordersApi": "https://api.example.com/orders"
        },
        "appConfig": {
          "maxUploadSize": 5242880,
          "defaultPageSize": 20
        }
      }
    }
  ]
}
```

### Error Codes

| Status Code | Description |
| --- | --- |
| 400 | Invalid `environment` parameter. |
| 500 | Internal server error. |

## DELETE /config

Deletes the remote configuration for a specific environment.

### Parameters

| Name | Type | Description |
| --- | --- | --- |
| `environment` | `string` | (Required) The environment to delete the configuration for (e.g. "production", "staging"). |

### Response

```json
{
  "message": "Configuration deleted successfully."
}
```

### Error Codes

| Status Code | Description |
| --- | --- |
| 400 | Invalid `environment` parameter. |
| 404 | Configuration not found for the specified environment. |
| 500 | Internal server error. |