---
title: A/B Testing API
description: Manage A/B tests, view results, and update experiment configurations.
keywords: [a/b testing, experiment, variant, analytics, optimization]
category: api-reference
---

## List Experiments
`GET /experiments`

### Parameters
| Name | Type | Description |
| --- | --- | --- |
| `page` | integer | Page number for paginated results |
| `limit` | integer | Number of results per page |
| `status` | string | Filter by experiment status (draft, running, completed) |

### Response
```json
{
  "data": [
    {
      "id": "abc123",
      "name": "Homepage Hero Banner",
      "description": "Test different hero banner designs",
      "status": "running",
      "variants": [
        {
          "id": "var1",
          "name": "Variant A",
          "traffic_allocation": 0.5
        },
        {
          "id": "var2", 
          "name": "Variant B",
          "traffic_allocation": 0.5
        }
      ],
      "start_date": "2023-04-01",
      "end_date": "2023-05-01"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 10,
    "total_results": 25
  }
}
```

## Get Experiment Details
`GET /experiments/{id}`

### Parameters
| Name | Type | Description |
| --- | --- | --- |
| `id` | string | Unique identifier of the experiment |

### Response
```json
{
  "id": "abc123",
  "name": "Homepage Hero Banner",
  "description": "Test different hero banner designs",
  "status": "running",
  "variants": [
    {
      "id": "var1",
      "name": "Variant A",
      "traffic_allocation": 0.5
    },
    {
      "id": "var2",
      "name": "Variant B", 
      "traffic_allocation": 0.5
    }
  ],
  "start_date": "2023-04-01",
  "end_date": "2023-05-01",
  "kpis": [
    {
      "name": "Clicks",
      "variant_results": [
        {
          "variant_id": "var1",
          "value": 1234
        },
        {
          "variant_id": "var2",
          "value": 987
        }
      ]
    },
    {
      "name": "Conversions",
      "variant_results": [
        {
          "variant_id": "var1",
          "value": 123
        },
        {
          "variant_id": "var2",
          "value": 78
        }
      ]
    }
  ]
}
```

## Create Experiment
`POST /experiments`

### Request Body
```json
{
  "name": "Homepage Hero Banner",
  "description": "Test different hero banner designs",
  "variants": [
    {
      "name": "Variant A",
      "traffic_allocation": 0.5
    },
    {
      "name": "Variant B",
      "traffic_allocation": 0.5
    }
  ],
  "start_date": "2023-04-01",
  "end_date": "2023-05-01",
  "kpis": [
    "Clicks",
    "Conversions"
  ]
}
```

### Response
```json
{
  "id": "abc123",
  "name": "Homepage Hero Banner",
  "description": "Test different hero banner designs",
  "status": "draft",
  "variants": [
    {
      "id": "var1",
      "name": "Variant A",
      "traffic_allocation": 0.5
    },
    {
      "id": "var2",
      "name": "Variant B",
      "traffic_allocation": 0.5
    }
  ],
  "start_date": "2023-04-01",
  "end_date": "2023-05-01",
  "kpis": [
    "Clicks",
    "Conversions"
  ]
}
```

## Update Experiment
`PUT /experiments/{id}`

### Parameters
| Name | Type | Description |
| --- | --- | --- |
| `id` | string | Unique identifier of the experiment |

### Request Body
```json
{
  "name": "Homepage Hero Banner v2",
  "description": "Test different hero banner designs with new variants",
  "variants": [
    {
      "id": "var1",
      "name": "Variant A",
      "traffic_allocation": 0.4
    },
    {
      "id": "var2",
      "name": "Variant B",
      "traffic_allocation": 0.4
    },
    {
      "id": "var3",
      "name": "Variant C",
      "traffic_allocation": 0.2
    }
  ],
  "start_date": "2023-04-15",
  "end_date": "2023-05-15",
  "kpis": [
    "Clicks",
    "Conversions",
    "Revenue"
  ]
}
```

### Response
```json
{
  "id": "abc123",
  "name": "Homepage Hero Banner v2",
  "description": "Test different hero banner designs with new variants",
  "status": "draft",
  "variants": [
    {
      "id": "var1",
      "name": "Variant A",
      "traffic_allocation": 0.4
    },
    {
      "id": "var2",
      "name": "Variant B",
      "traffic_allocation": 0.4
    },
    {
      "id": "var3",
      "name": "Variant C",
      "traffic_allocation": 0.2
    }
  ],
  "start_date": "2023-04-15",
  "end_date": "2023-05-15",
  "kpis": [
    "Clicks",
    "Conversions",
    "Revenue"
  ]
}
```

## Error Codes
| Status Code | Description |
| --- | --- |
| 400 | Bad Request - Invalid input data |
| 404 | Not Found - Experiment not found |
| 409 | Conflict - Experiment with the same name already exists |
| 500 | Internal Server Error - An unexpected error occurred |