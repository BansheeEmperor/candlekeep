---
title: Canary Release API
description: API for managing canary releases of software updates
keywords: [canary, release, deployment, feature-flag, software-updates]
category: api-reference
---

## POST /canary/start
Initiate a new canary release for a software update.

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| service | string | The name of the service to deploy the canary update for | Yes |
| version | string | The version of the update to deploy as a canary | Yes |
| percentage | integer | The percentage of traffic to route to the canary (1-100) | Yes |
| timeout | integer | The duration (in minutes) to run the canary before rolling back | Yes |

### Request Body
```json
{
  "service": "my-app",
  "version": "v1.2.3",
  "percentage": 10,
  "timeout": 60
}
```

### Response
```json
{
  "id": "c12345",
  "service": "my-app",
  "version": "v1.2.3",
  "percentage": 10,
  "timeout": 60,
  "status": "active",
  "created_at": "2023-04-01T12:00:00Z"
}
```

### Error Codes
- `400 Bad Request`: Missing or invalid parameters
- `409 Conflict`: A canary release is already active for the specified service

## GET /canary
Retrieve a list of all active canary releases.

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| service | string | Filter by the name of the service | No |
| status | string | Filter by the status of the canary release (active, completed, failed) | No |

### Response
```json
[
  {
    "id": "c12345",
    "service": "my-app",
    "version": "v1.2.3",
    "percentage": 10,
    "timeout": 60,
    "status": "active",
    "created_at": "2023-04-01T12:00:00Z"
  },
  {
    "id": "c67890",
    "service": "other-app",
    "version": "v2.0.1",
    "percentage": 20,
    "timeout": 90,
    "status": "completed",
    "created_at": "2023-03-15T09:30:00Z"
  }
]
```

### Error Codes
- `400 Bad Request`: Invalid filter parameters

## GET /canary/{id}
Retrieve details of a specific canary release.

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| id | string | The ID of the canary release to retrieve | Yes |

### Response
```json
{
  "id": "c12345",
  "service": "my-app",
  "version": "v1.2.3",
  "percentage": 10,
  "timeout": 60,
  "status": "active",
  "created_at": "2023-04-01T12:00:00Z"
}
```

### Error Codes
- `404 Not Found`: Canary release with the specified ID not found

## POST /canary/{id}/complete
Manually complete a canary release.

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| id | string | The ID of the canary release to complete | Yes |

### Response
```json
{
  "id": "c12345",
  "service": "my-app",
  "version": "v1.2.3",
  "percentage": 10,
  "timeout": 60,
  "status": "completed",
  "created_at": "2023-04-01T12:00:00Z",
  "completed_at": "2023-04-01T13:15:00Z"
}
```

### Error Codes
- `404 Not Found`: Canary release with the specified ID not found
- `409 Conflict`: Canary release is not in an active state

## DELETE /canary/{id}
Abort a canary release.

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| id | string | The ID of the canary release to abort | Yes |

### Response
```json
{
  "id": "c12345",
  "service": "my-app",
  "version": "v1.2.3",
  "percentage": 10,
  "timeout": 60,
  "status": "aborted",
  "created_at": "2023-04-01T12:00:00Z",
  "aborted_at": "2023-04-01T12:30:00Z"
}
```

### Error Codes
- `404 Not Found`: Canary release with the specified ID not found