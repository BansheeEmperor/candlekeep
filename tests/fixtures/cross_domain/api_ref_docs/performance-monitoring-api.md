---
title: Performance Monitoring API
description: REST API for querying performance metrics and alerts
keywords: [performance, monitoring, metrics, alerts, analytics]
category: api-reference
---

## GET /metrics
Retrieve performance metrics for a given time range.

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `start_time` | string | true | Start time in ISO 8601 format (e.g. `2023-04-01T00:00:00Z`) |
| `end_time` | string | true | End time in ISO 8601 format (e.g. `2023-04-01T23:59:59Z`) |
| `metric` | string | true | Metric to retrieve (e.g. `cpu_utilization`, `memory_usage`, `network_throughput`) |
| `granularity` | string | false | Time granularity (e.g. `1m`, `5m`, `1h`), default is `1m` |
| `entity_id` | string | false | Filter metrics by entity ID |

### Response

```json
{
  "data": [
    {
      "timestamp": "2023-04-01T00:00:00Z",
      "value": 75.2
    },
    {
      "timestamp": "2023-04-01T00:01:00Z",
      "value": 78.1
    },
    // ... more data points
  ]
}
```

### Error Codes

| Status Code | Description |
| --- | --- |
| 400 | Invalid request parameters |
| 404 | Metric not found |
| 500 | Internal server error |

## GET /alerts
Retrieve performance alerts for a given time range.

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `start_time` | string | true | Start time in ISO 8601 format (e.g. `2023-04-01T00:00:00Z`) |
| `end_time` | string | true | End time in ISO 8601 format (e.g. `2023-04-01T23:59:59Z`) |
| `severity` | string | false | Filter alerts by severity (e.g. `critical`, `warning`) |
| `status` | string | false | Filter alerts by status (e.g. `open`, `resolved`) |
| `entity_id` | string | false | Filter alerts by entity ID |

### Response

```json
{
  "data": [
    {
      "id": "alert-123",
      "timestamp": "2023-04-01T10:15:00Z",
      "metric": "cpu_utilization",
      "severity": "critical",
      "status": "open",
      "entity_id": "server-abc",
      "description": "CPU utilization exceeds 90% on server-abc"
    },
    {
      "id": "alert-456",
      "timestamp": "2023-04-01T14:30:00Z",
      "metric": "memory_usage",
      "severity": "warning",
      "status": "resolved",
      "entity_id": "server-xyz",
      "description": "Memory usage is high on server-xyz"
    },
    // ... more alerts
  ]
}
```

### Error Codes

| Status Code | Description |
| --- | --- |
| 400 | Invalid request parameters |
| 500 | Internal server error |

## POST /alerts
Create a new performance alert.

### Request Body

```json
{
  "metric": "cpu_utilization",
  "threshold": 80,
  "severity": "critical",
  "entity_id": "server-abc",
  "description": "CPU utilization exceeds 80% on server-abc"
}
```

### Response

```json
{
  "id": "alert-789",
  "timestamp": "2023-04-02T08:00:00Z",
  "metric": "cpu_utilization",
  "threshold": 80,
  "severity": "critical",
  "status": "open",
  "entity_id": "server-abc",
  "description": "CPU utilization exceeds 80% on server-abc"
}
```

### Error Codes

| Status Code | Description |
| --- | --- |
| 400 | Invalid request body |
| 409 | Alert already exists for the same metric, entity, and severity |
| 500 | Internal server error |

## PATCH /alerts/{id}
Update the status of a performance alert.

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | string | true | ID of the alert to update |

### Request Body

```json
{
  "status": "resolved"
}
```

### Response

```json
{
  "id": "alert-789",
  "timestamp": "2023-04-02T08:00:00Z",
  "metric": "cpu_utilization",
  "threshold": 80,
  "severity": "critical",
  "status": "resolved",
  "entity_id": "server-abc",
  "description": "CPU utilization exceeds 80% on server-abc"
}
```

### Error Codes

| Status Code | Description |
| --- | --- |
| 400 | Invalid request body |
| 404 | Alert not found |
| 500 | Internal server error |