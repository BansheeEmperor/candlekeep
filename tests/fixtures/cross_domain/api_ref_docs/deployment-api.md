---
title: Deployment API
description: API for managing deployments of your application
keywords: [deployment, release, environment, infrastructure, application]
category: api-reference
---

## GET /deployments
Retrieve a list of all deployments.

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| environment | string | Filter deployments by environment | No |
| status | string | Filter deployments by status (e.g. "pending", "in_progress", "succeeded", "failed") | No |
| page | integer | Page number for pagination | No |
| per_page | integer | Number of results per page | No |

### Response
```json
{
  "data": [
    {
      "id": "1234567890",
      "environment": "production",
      "version": "v1.2.3",
      "status": "succeeded",
      "started_at": "2023-04-01T12:00:00Z",
      "completed_at": "2023-04-01T12:05:00Z",
      "created_at": "2023-03-31T16:30:00Z",
      "updated_at": "2023-04-01T12:05:00Z"
    },
    {
      "id": "0987654321",
      "environment": "staging",
      "version": "v1.2.2",
      "status": "failed",
      "started_at": "2023-03-31T15:00:00Z",
      "completed_at": "2023-03-31T15:15:00Z",
      "created_at": "2023-03-30T10:00:00Z",
      "updated_at": "2023-03-31T15:15:00Z"
    }
  ],
  "meta": {
    "total_count": 25,
    "total_pages": 5,
    "current_page": 1
  }
}
```

## POST /deployments
Create a new deployment.

### Request Body
```json
{
  "environment": "production",
  "version": "v1.2.3",
  "commit_sha": "abcd1234",
  "description": "Deploy new features and bug fixes"
}
```

### Response
```json
{
  "id": "1234567890",
  "environment": "production",
  "version": "v1.2.3",
  "status": "pending",
  "started_at": "2023-04-01T12:00:00Z",
  "completed_at": null,
  "created_at": "2023-04-01T12:00:00Z",
  "updated_at": "2023-04-01T12:00:00Z"
}
```

## GET /deployments/{id}
Retrieve details of a specific deployment.

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| id | string | ID of the deployment | Yes |

### Response
```json
{
  "id": "1234567890",
  "environment": "production",
  "version": "v1.2.3",
  "status": "succeeded",
  "started_at": "2023-04-01T12:00:00Z",
  "completed_at": "2023-04-01T12:05:00Z",
  "created_at": "2023-03-31T16:30:00Z",
  "updated_at": "2023-04-01T12:05:00Z",
  "commit_sha": "abcd1234",
  "description": "Deploy new features and bug fixes"
}
```

## PATCH /deployments/{id}
Update the status of a deployment.

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| id | string | ID of the deployment | Yes |

### Request Body
```json
{
  "status": "in_progress"
}
```

### Response
```json
{
  "id": "1234567890",
  "environment": "production",
  "version": "v1.2.3",
  "status": "in_progress",
  "started_at": "2023-04-01T12:00:00Z",
  "completed_at": null,
  "created_at": "2023-03-31T16:30:00Z",
  "updated_at": "2023-04-01T12:01:00Z",
  "commit_sha": "abcd1234",
  "description": "Deploy new features and bug fixes"
}
```

## Error Codes
| Status Code | Description |
| --- | --- |
| 400 Bad Request | Invalid request parameters or body |
| 404 Not Found | Deployment not found |
| 422 Unprocessable Entity | Unable to process the request |
| 500 Internal Server Error | An unexpected error occurred |