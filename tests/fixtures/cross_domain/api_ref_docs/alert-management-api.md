---
title: Alert Management API
description: Manage alerts and notifications for your application
keywords: [alerts, notifications, events, monitoring, incident management]
category: api-reference
---

## GET /alerts
Retrieve a list of all active alerts.

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `status` | string | No | Filter alerts by status (e.g. `active`, `resolved`) |
| `severity` | string | No | Filter alerts by severity (e.g. `critical`, `warning`, `info`) |
| `page` | integer | No | Page number for pagination (default: 1) |
| `limit` | integer | No | Number of results per page (default: 20, max: 100) |

### Response

```json
{
  "data": [
    {
      "id": "abc123",
      "name": "High CPU Usage",
      "description": "Server CPU utilization is above 90%",
      "severity": "critical",
      "status": "active",
      "created_at": "2023-04-01T12:34:56Z",
      "updated_at": "2023-04-01T12:35:00Z"
    },
    {
      "id": "def456",
      "name": "Disk Space Low",
      "description": "Disk space on volume /data is below 10%",
      "severity": "warning",
      "status": "active",
      "created_at": "2023-03-31T15:22:11Z",
      "updated_at": "2023-03-31T15:22:15Z"
    }
  ],
  "meta": {
    "total": 25,
    "page": 1,
    "limit": 20
  }
}
```

## GET /alerts/{id}
Retrieve details of a specific alert.

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | string | Yes | The ID of the alert |

### Response

```json
{
  "data": {
    "id": "abc123",
    "name": "High CPU Usage",
    "description": "Server CPU utilization is above 90%",
    "severity": "critical",
    "status": "active",
    "created_at": "2023-04-01T12:34:56Z",
    "updated_at": "2023-04-01T12:35:00Z"
  }
}
```

## POST /alerts
Create a new alert.

### Request Body

```json
{
  "name": "Disk Space Low",
  "description": "Disk space on volume /data is below 10%",
  "severity": "warning",
  "status": "active"
}
```

### Response

```json
{
  "data": {
    "id": "def456",
    "name": "Disk Space Low",
    "description": "Disk space on volume /data is below 10%",
    "severity": "warning",
    "status": "active",
    "created_at": "2023-04-02T09:15:22Z",
    "updated_at": "2023-04-02T09:15:22Z"
  }
}
```

## PATCH /alerts/{id}
Update an existing alert.

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | string | Yes | The ID of the alert |

### Request Body

```json
{
  "status": "resolved",
  "updated_at": "2023-04-02T10:30:00Z"
}
```

### Response

```json
{
  "data": {
    "id": "def456",
    "name": "Disk Space Low",
    "description": "Disk space on volume /data is below 10%",
    "severity": "warning",
    "status": "resolved",
    "created_at": "2023-04-02T09:15:22Z",
    "updated_at": "2023-04-02T10:30:00Z"
  }
}
```

## DELETE /alerts/{id}
Delete an existing alert.

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | string | Yes | The ID of the alert |

### Response

```json
{
  "data": {
    "id": "def456",
    "name": "Disk Space Low",
    "description": "Disk space on volume /data is below 10%",
    "severity": "warning",
    "status": "resolved",
    "created_at": "2023-04-02T09:15:22Z",
    "updated_at": "2023-04-02T10:30:00Z"
  }
}
```

### Error Codes

| Status Code | Description |
| --- | --- |
| 400 Bad Request | Invalid request parameters or body |
| 404 Not Found | The requested alert was not found |
| 500 Internal Server Error | An unexpected error occurred on the server |