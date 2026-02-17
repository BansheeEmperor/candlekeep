---
title: Analytics Reporting API
description: API for retrieving analytics data for your business
keywords: [analytics, reporting, metrics, data, business intelligence]
category: api-reference
---

## GET /analytics/reports
Retrieve a list of available analytics reports.

### Parameters
| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `start_date` | string | true | Start date for report data (YYYY-MM-DD) |
| `end_date` | string | true | End date for report data (YYYY-MM-DD) |
| `metrics` | string | false | Comma-separated list of metric names to include |
| `dimensions` | string | false | Comma-separated list of dimension names to include |

### Response
```json
{
  "reports": [
    {
      "id": "revenue_by_product",
      "name": "Revenue by Product",
      "description": "Total revenue broken down by product"
    },
    {
      "id": "user_engagement",
      "name": "User Engagement",
      "description": "User activity metrics like sessions, pageviews, etc."
    },
    {
      "id": "marketing_campaign_performance",
      "name": "Marketing Campaign Performance",
      "description": "Effectiveness of marketing campaigns"
    }
  ]
}
```

## GET /analytics/reports/{report_id}
Retrieve data for a specific analytics report.

### Parameters
| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `report_id` | string | true | ID of the report to retrieve |
| `start_date` | string | true | Start date for report data (YYYY-MM-DD) |
| `end_date` | string | true | End date for report data (YYYY-MM-DD) |
| `metrics` | string | false | Comma-separated list of metric names to include |
| `dimensions` | string | false | Comma-separated list of dimension names to include |
| `limit` | integer | false | Maximum number of rows to return (default 100) |
| `offset` | integer | false | Number of rows to skip (for pagination) |

### Response
```json
{
  "report_id": "revenue_by_product",
  "dimensions": [
    "product_name",
    "product_category"
  ],
  "metrics": [
    "revenue",
    "units_sold"
  ],
  "data": [
    {
      "product_name": "Widget A",
      "product_category": "Gadgets",
      "revenue": 25000.00,
      "units_sold": 1250
    },
    {
      "product_name": "Gizmo X",
      "product_category": "Gadgets",
      "revenue": 18500.00,
      "units_sold": 850
    },
    {
      "product_name": "Thingamajig",
      "product_category": "Widgets",
      "revenue": 12000.00,
      "units_sold": 600
    }
  ]
}
```

## POST /analytics/custom_report
Create a custom analytics report.

### Request Body
```json
{
  "name": "New Sales Report",
  "description": "Custom report for sales data",
  "metrics": [
    "revenue",
    "units_sold",
    "new_customers"
  ],
  "dimensions": [
    "product_name",
    "product_category",
    "sales_rep"
  ],
  "filters": [
    {
      "field": "product_category",
      "operator": "in",
      "values": ["Gadgets", "Widgets"]
    },
    {
      "field": "sales_rep",
      "operator": "equals",
      "values": ["John Doe"]
    }
  ],
  "sort": [
    {
      "field": "revenue",
      "direction": "desc"
    }
  ],
  "limit": 50,
  "offset": 0
}
```

### Response
```json
{
  "id": "custom_report_123",
  "name": "New Sales Report",
  "description": "Custom report for sales data",
  "metrics": [
    "revenue",
    "units_sold",
    "new_customers"
  ],
  "dimensions": [
    "product_name",
    "product_category",
    "sales_rep"
  ],
  "filters": [
    {
      "field": "product_category",
      "operator": "in",
      "values": ["Gadgets", "Widgets"]
    },
    {
      "field": "sales_rep",
      "operator": "equals",
      "values": ["John Doe"]
    }
  ],
  "sort": [
    {
      "field": "revenue",
      "direction": "desc"
    }
  ],
  "limit": 50,
  "offset": 0,
  "data": [
    {
      "product_name": "Widget A",
      "product_category": "Gadgets",
      "sales_rep": "John Doe",
      "revenue": 25000.00,
      "units_sold": 1250,
      "new_customers": 75
    },
    {
      "product_name": "Gizmo X",
      "product_category": "Gadgets",
      "sales_rep": "John Doe",
      "revenue": 18500.00,
      "units_sold": 850,
      "new_customers": 50
    },
    {
      "product_name": "Thingamajig",
      "product_category": "Widgets",
      "sales_rep": "John Doe",
      "revenue": 12000.00,
      "units_sold": 600,
      "new_customers": 30
    }
  ]
}
```

## DELETE /analytics/custom_reports/{report_id}
Delete a custom analytics report.

### Parameters
| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `report_id` | string | true | ID of the custom report to delete |

### Response
```json
{
  "message": "Custom report deleted successfully"
}
```

### Error Codes
| HTTP Status | Error Code | Description |
| --- | --- | --- |
| 400 | INVALID_REQUEST | One or more request parameters are invalid |
| 401 | UNAUTHORIZED | Invalid or missing API credentials |
| 404 | NOT_FOUND | The requested resource was not found |
| 500 | INTERNAL_SERVER_ERROR | An unexpected error occurred on the server |