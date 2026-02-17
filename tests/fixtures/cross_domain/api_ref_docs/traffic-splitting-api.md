---
title: Traffic Splitting API
description: Programmatically configure traffic splitting rules for your application.
keywords: [traffic splitting, load balancing, canary releases, feature flags, gradual rollouts]
category: api-reference
---

## `POST /v1/traffic-splits`
Create a new traffic splitting rule.

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| name | string | A unique name for the traffic splitting rule. | Yes |
| description | string | A brief description of the rule. | No |
| targets | array[object] | The targets to split traffic between. | Yes |

### Request Body
```json
{
  "name": "my-feature-rollout",
  "description": "Gradually roll out new feature to 25% of users",
  "targets": [
    {
      "name": "control",
      "percentage": 75
    },
    {
      "name": "experiment",
      "percentage": 25
    }
  ]
}
```

### Response
```json
{
  "id": "abc123",
  "name": "my-feature-rollout",
  "description": "Gradually roll out new feature to 25% of users",
  "targets": [
    {
      "name": "control",
      "percentage": 75
    },
    {
      "name": "experiment",
      "percentage": 25
    }
  ],
  "createdAt": "2023-04-01T12:00:00Z",
  "updatedAt": "2023-04-01T12:00:00Z"
}
```

### Error Codes
- `400 Bad Request`: Invalid request body or parameters.
- `409 Conflict`: A rule with the same name already exists.

## `GET /v1/traffic-splits`
List all traffic splitting rules.

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| page | integer | The page number to retrieve. | No |
| per_page | integer | The number of results to return per page. | No |

### Response
```json
{
  "data": [
    {
      "id": "abc123",
      "name": "my-feature-rollout",
      "description": "Gradually roll out new feature to 25% of users",
      "targets": [
        {
          "name": "control",
          "percentage": 75
        },
        {
          "name": "experiment",
          "percentage": 25
        }
      ],
      "createdAt": "2023-04-01T12:00:00Z",
      "updatedAt": "2023-04-01T12:00:00Z"
    },
    {
      "id": "def456",
      "name": "new-homepage-test",
      "description": "A/B test for the new homepage design",
      "targets": [
        {
          "name": "original",
          "percentage": 50
        },
        {
          "name": "variant-a",
          "percentage": 25
        },
        {
          "name": "variant-b",
          "percentage": 25
        }
      ],
      "createdAt": "2023-03-15T09:30:00Z",
      "updatedAt": "2023-03-20T14:45:00Z"
    }
  ],
  "meta": {
    "page": 1,
    "per_page": 10,
    "total_count": 2
  }
}
```

## `GET /v1/traffic-splits/{id}`
Retrieve a specific traffic splitting rule.

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| id | string | The ID of the traffic splitting rule. | Yes |

### Response
```json
{
  "id": "abc123",
  "name": "my-feature-rollout",
  "description": "Gradually roll out new feature to 25% of users",
  "targets": [
    {
      "name": "control",
      "percentage": 75
    },
    {
      "name": "experiment",
      "percentage": 25
    }
  ],
  "createdAt": "2023-04-01T12:00:00Z",
  "updatedAt": "2023-04-01T12:00:00Z"
}
```

### Error Codes
- `404 Not Found`: The specified traffic splitting rule does not exist.

## `PATCH /v1/traffic-splits/{id}`
Update an existing traffic splitting rule.

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| id | string | The ID of the traffic splitting rule. | Yes |

### Request Body
```json
{
  "name": "my-feature-rollout",
  "description": "Gradually roll out new feature to 50% of users",
  "targets": [
    {
      "name": "control",
      "percentage": 50
    },
    {
      "name": "experiment",
      "percentage": 50
    }
  ]
}
```

### Response
```json
{
  "id": "abc123",
  "name": "my-feature-rollout",
  "description": "Gradually roll out new feature to 50% of users",
  "targets": [
    {
      "name": "control",
      "percentage": 50
    },
    {
      "name": "experiment",
      "percentage": 50
    }
  ],
  "createdAt": "2023-04-01T12:00:00Z",
  "updatedAt": "2023-04-02T15:30:00Z"
}
```

### Error Codes
- `404 Not Found`: The specified traffic splitting rule does not exist.
- `400 Bad Request`: Invalid request body or parameters.