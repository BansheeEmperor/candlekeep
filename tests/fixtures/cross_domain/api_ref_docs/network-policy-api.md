---
title: Network Policy API
description: API for managing network policies in a cloud environment
keywords: [network, policy, cloud, security, firewall, access control]
category: api-reference
---

## GET /network-policies
Retrieve a list of all network policies.

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| page | integer | The page number to retrieve (default: 1) | No |
| per_page | integer | The number of results per page (default: 20) | No |
| name | string | Filter policies by name | No |
| application | string | Filter policies by associated application | No |

### Response
```json
{
  "data": [
    {
      "id": "123456789",
      "name": "Allow HTTP traffic",
      "application": "web-app",
      "source": {
        "type": "cidr",
        "value": "0.0.0.0/0"
      },
      "destination": {
        "type": "service",
        "value": "http"
      },
      "action": "allow",
      "priority": 100
    },
    {
      "id": "987654321",
      "name": "Deny SSH access",
      "application": "database",
      "source": {
        "type": "cidr",
        "value": "0.0.0.0/0"
      },
      "destination": {
        "type": "service",
        "value": "ssh"
      },
      "action": "deny",
      "priority": 50
    }
  ],
  "meta": {
    "total": 2,
    "page": 1,
    "per_page": 20
  }
}
```

### Error Codes
| Code | Description |
| --- | --- |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 500 | Internal Server Error |

## POST /network-policies
Create a new network policy.

### Request Body
```json
{
  "name": "Allow HTTP traffic",
  "application": "web-app",
  "source": {
    "type": "cidr",
    "value": "0.0.0.0/0"
  },
  "destination": {
    "type": "service",
    "value": "http"
  },
  "action": "allow",
  "priority": 100
}
```

### Response
```json
{
  "id": "123456789",
  "name": "Allow HTTP traffic",
  "application": "web-app",
  "source": {
    "type": "cidr",
    "value": "0.0.0.0/0"
  },
  "destination": {
    "type": "service",
    "value": "http"
  },
  "action": "allow",
  "priority": 100
}
```

### Error Codes
| Code | Description |
| --- | --- |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 500 | Internal Server Error |

## GET /network-policies/{id}
Retrieve a specific network policy.

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| id | string | The ID of the network policy to retrieve | Yes |

### Response
```json
{
  "id": "123456789",
  "name": "Allow HTTP traffic",
  "application": "web-app",
  "source": {
    "type": "cidr",
    "value": "0.0.0.0/0"
  },
  "destination": {
    "type": "service",
    "value": "http"
  },
  "action": "allow",
  "priority": 100
}
```

### Error Codes
| Code | Description |
| --- | --- |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 500 | Internal Server Error |

## PUT /network-policies/{id}
Update an existing network policy.

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| id | string | The ID of the network policy to update | Yes |

### Request Body
```json
{
  "name": "Allow HTTP and HTTPS traffic",
  "application": "web-app",
  "source": {
    "type": "cidr",
    "value": "0.0.0.0/0"
  },
  "destination": {
    "type": "service",
    "value": ["http", "https"]
  },
  "action": "allow",
  "priority": 100
}
```

### Response
```json
{
  "id": "123456789",
  "name": "Allow HTTP and HTTPS traffic",
  "application": "web-app",
  "source": {
    "type": "cidr",
    "value": "0.0.0.0/0"
  },
  "destination": {
    "type": "service",
    "value": ["http", "https"]
  },
  "action": "allow",
  "priority": 100
}
```

### Error Codes
| Code | Description |
| --- | --- |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 500 | Internal Server Error |