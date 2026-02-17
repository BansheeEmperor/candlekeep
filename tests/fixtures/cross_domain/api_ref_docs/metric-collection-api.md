---
title: Metric Collection API
description: A RESTful API for collecting and managing metrics data.
keywords: [metrics, data collection, time series, analytics, monitoring]
category: api-reference
---

## GET /metrics
Retrieves a list of all available metrics.

### Parameters
| Name | Type | Description |
| --- | --- | --- |
| `page` | integer | The page number to retrieve (default: 1) |
| `limit` | integer | The number of results to return per page (default: 20, max: 100) |
| `sort` | string | The field to sort the results by (default: `name`) |
| `order` | string | The sort order (asc or desc, default: asc) |

### Response
```json
{
  "data": [
    {
      "id": "1234",
      "name": "CPU Utilization",
      "description": "Percentage of CPU usage",
      "type": "gauge",
      "unit": "%"
    },
    {
      "id": "5678",
      "name": "Memory Usage",
      "description": "Amount of memory used",
      "type": "gauge",
      "unit": "bytes"
    }
  ],
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 50
  }
}
```

## POST /metrics
Creates a new metric.

### Request Body
```json
{
  "name": "Disk Utilization",
  "description": "Percentage of disk space used",
  "type": "gauge",
  "unit": "%"
}
```

### Response
```json
{
  "id": "9012",
  "name": "Disk Utilization",
  "description": "Percentage of disk space used",
  "type": "gauge",
  "unit": "%"
}
```

## GET /metrics/{id}
Retrieves a specific metric by its ID.

### Parameters
| Name | Type | Description |
| --- | --- | --- |
| `id` | string | The ID of the metric to retrieve |

### Response
```json
{
  "id": "1234",
  "name": "CPU Utilization",
  "description": "Percentage of CPU usage",
  "type": "gauge",
  "unit": "%"
}
```

## POST /metrics/{id}/data
Adds a new data point to the specified metric.

### Parameters
| Name | Type | Description |
| --- | --- | --- |
| `id` | string | The ID of the metric to add data to |

### Request Body
```json
{
  "timestamp": "2023-04-01T12:00:00Z",
  "value": 75.3
}
```

### Response
```json
{
  "id": "1234",
  "timestamp": "2023-04-01T12:00:00Z",
  "value": 75.3
}
```

## GET /metrics/{id}/data
Retrieves the data points for the specified metric.

### Parameters
| Name | Type | Description |
| --- | --- | --- |
| `id` | string | The ID of the metric to retrieve data for |
| `start` | string | The start time for the data (ISO 8601 format) |
| `end` | string | The end time for the data (ISO 8601 format) |
| `limit` | integer | The maximum number of data points to return (default: 100, max: 1000) |

### Response
```json
{
  "data": [
    {
      "id": "1234",
      "timestamp": "2023-04-01T12:00:00Z",
      "value": 75.3
    },
    {
      "id": "1234",
      "timestamp": "2023-04-01T12:00:01Z",
      "value": 75.4
    },
    {
      "id": "1234",
      "timestamp": "2023-04-01T12:00:02Z",
      "value": 75.2
    }
  ]
}
```

## Error Codes
| Status Code | Description |
| --- | --- |
| 400 Bad Request | The request was malformed or invalid. |
| 404 Not Found | The requested resource was not found. |
| 409 Conflict | The request could not be completed due to a conflict. |
| 500 Internal Server Error | An unexpected error occurred on the server. |