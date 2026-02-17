---
title: Firewall Rules API
description: API for managing firewall rules in a cloud-based network infrastructure.
keywords: [firewall, network security, access control, cloud infrastructure]
category: api-reference
---

## List Firewall Rules
`GET /api/v1/firewall-rules`

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| page | integer | No | The page number to retrieve (default: 1) |
| per_page | integer | No | The number of results per page (default: 20, max: 100) |
| search | string | No | Search query to filter results |

### Response

```json
{
  "data": [
    {
      "id": "1234",
      "name": "Allow HTTP Traffic",
      "source_ip": "0.0.0.0/0",
      "destination_ip": "10.0.1.0/24",
      "protocol": "tcp",
      "port_range": "80-80",
      "action": "allow",
      "priority": 10,
      "created_at": "2023-04-01T12:00:00Z",
      "updated_at": "2023-04-01T12:00:00Z"
    },
    {
      "id": "5678",
      "name": "Deny SSH Traffic",
      "source_ip": "0.0.0.0/0",
      "destination_ip": "10.0.2.0/24",
      "protocol": "tcp",
      "port_range": "22-22",
      "action": "deny",
      "priority": 20,
      "created_at": "2023-04-01T12:00:00Z",
      "updated_at": "2023-04-01T12:00:00Z"
    }
  ],
  "meta": {
    "total": 2,
    "page": 1,
    "per_page": 20
  }
}
```

## Create a Firewall Rule
`POST /api/v1/firewall-rules`

### Request Body

```json
{
  "name": "Allow HTTP Traffic",
  "source_ip": "0.0.0.0/0",
  "destination_ip": "10.0.1.0/24",
  "protocol": "tcp",
  "port_range": "80-80",
  "action": "allow",
  "priority": 10
}
```

### Response

```json
{
  "id": "1234",
  "name": "Allow HTTP Traffic",
  "source_ip": "0.0.0.0/0",
  "destination_ip": "10.0.1.0/24",
  "protocol": "tcp",
  "port_range": "80-80",
  "action": "allow",
  "priority": 10,
  "created_at": "2023-04-01T12:00:00Z",
  "updated_at": "2023-04-01T12:00:00Z"
}
```

## Update a Firewall Rule
`PUT /api/v1/firewall-rules/{id}`

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| id | string | Yes | The ID of the firewall rule to update |

### Request Body

```json
{
  "name": "Allow HTTP and HTTPS Traffic",
  "source_ip": "0.0.0.0/0",
  "destination_ip": "10.0.1.0/24",
  "protocol": "tcp",
  "port_range": "80-443",
  "action": "allow",
  "priority": 10
}
```

### Response

```json
{
  "id": "1234",
  "name": "Allow HTTP and HTTPS Traffic",
  "source_ip": "0.0.0.0/0",
  "destination_ip": "10.0.1.0/24",
  "protocol": "tcp",
  "port_range": "80-443",
  "action": "allow",
  "priority": 10,
  "created_at": "2023-04-01T12:00:00Z",
  "updated_at": "2023-04-02T10:30:00Z"
}
```

## Delete a Firewall Rule
`DELETE /api/v1/firewall-rules/{id}`

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| id | string | Yes | The ID of the firewall rule to delete |

### Response

No content is returned on successful deletion. The HTTP status code will be `204 No Content`.

## Error Codes

| Status Code | Description |
| --- | --- |
| 400 Bad Request | The request was malformed or invalid. |
| 401 Unauthorized | The request was not authorized. |
| 404 Not Found | The requested resource was not found. |
| 409 Conflict | The request could not be completed due to a conflict. |
| 500 Internal Server Error | An unexpected error occurred on the server. |