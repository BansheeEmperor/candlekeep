---
title: Feature Flag API
description: API for managing feature flags in your application
keywords: [feature flags, toggles, configuration, environment, release management]
category: api-reference
---

## GET /features
Retrieve a list of all feature flags.

### Parameters
| Name | Type | Description |
| --- | --- | --- |
| `environment` | string | (optional) Filter features by environment |
| `page` | integer | (optional) Page number for pagination |
| `per_page` | integer | (optional) Number of results per page |

### Response
```json
{
  "data": [
    {
      "id": "123",
      "name": "new_homepage_design",
      "description": "Updated homepage layout and styling",
      "enabled": true,
      "environment": "production"
    },
    {
      "id": "456",
      "name": "mobile_signup_flow",
      "description": "Simplified mobile sign up process",
      "enabled": false,
      "environment": "staging"
    }
  ],
  "meta": {
    "total_count": 25,
    "total_pages": 5,
    "current_page": 1
  }
}
```

### Error Codes
| Status Code | Description |
| --- | --- |
| 400 | Invalid request parameters |
| 500 | Internal server error |

## GET /features/{id}
Retrieve details of a specific feature flag.

### Parameters
| Name | Type | Description |
| --- | --- | --- |
| `id` | string | ID of the feature flag |

### Response
```json
{
  "data": {
    "id": "123",
    "name": "new_homepage_design",
    "description": "Updated homepage layout and styling",
    "enabled": true,
    "environment": "production",
    "created_at": "2023-04-01T12:00:00Z",
    "updated_at": "2023-04-15T09:30:00Z"
  }
}
```

### Error Codes
| Status Code | Description |
| --- | --- |
| 404 | Feature flag not found |
| 500 | Internal server error |

## POST /features
Create a new feature flag.

### Request Body
```json
{
  "name": "mobile_signup_flow",
  "description": "Simplified mobile sign up process",
  "enabled": false,
  "environment": "staging"
}
```

### Response
```json
{
  "data": {
    "id": "456",
    "name": "mobile_signup_flow",
    "description": "Simplified mobile sign up process",
    "enabled": false,
    "environment": "staging",
    "created_at": "2023-04-20T15:45:00Z",
    "updated_at": "2023-04-20T15:45:00Z"
  }
}
```

### Error Codes
| Status Code | Description |
| --- | --- |
| 400 | Invalid request body |
| 409 | Feature flag with the same name already exists |
| 500 | Internal server error |

## PATCH /features/{id}
Update an existing feature flag.

### Parameters
| Name | Type | Description |
| --- | --- | --- |
| `id` | string | ID of the feature flag |

### Request Body
```json
{
  "name": "mobile_signup_flow",
  "description": "Simplified mobile sign up process v2",
  "enabled": true
}
```

### Response
```json
{
  "data": {
    "id": "456",
    "name": "mobile_signup_flow",
    "description": "Simplified mobile sign up process v2",
    "enabled": true,
    "environment": "staging",
    "created_at": "2023-04-20T15:45:00Z",
    "updated_at": "2023-04-21T11:30:00Z"
  }
}
```

### Error Codes
| Status Code | Description |
| --- | --- |
| 404 | Feature flag not found |
| 400 | Invalid request body |
| 500 | Internal server error |

## DELETE /features/{id}
Delete a feature flag.

### Parameters
| Name | Type | Description |
| --- | --- | --- |
| `id` | string | ID of the feature flag |

### Response
```json
{
  "data": {
    "id": "456",
    "name": "mobile_signup_flow",
    "description": "Simplified mobile sign up process v2",
    "enabled": true,
    "environment": "staging",
    "created_at": "2023-04-20T15:45:00Z",
    "updated_at": "2023-04-21T11:30:00Z",
    "deleted_at": "2023-04-22T09:00:00Z"
  }
}
```

### Error Codes
| Status Code | Description |
| --- | --- |
| 404 | Feature flag not found |
| 500 | Internal server error |