---
title: Compliance Reporting API
description: An API for generating compliance reports for regulatory agencies
keywords: [compliance, reporting, regulation, audit, financial]
category: api-reference
---

## GET /compliance/reports
Retrieves a list of all compliance reports.

### Parameters
| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| `start_date` | string | The start date for the report period (YYYY-MM-DD) | Yes |
| `end_date` | string | The end date for the report period (YYYY-MM-DD) | Yes |
| `entity_id` | string | The ID of the entity to filter reports for | No |
| `report_type` | string | The type of report to filter by (e.g. "financial", "hr") | No |

### Response
```json
{
  "reports": [
    {
      "id": "report_123",
      "entity_id": "entity_abc",
      "report_type": "financial",
      "period_start": "2022-01-01",
      "period_end": "2022-12-31",
      "status": "completed",
      "url": "https://example.com/report_123.pdf"
    },
    {
      "id": "report_456",
      "entity_id": "entity_xyz",
      "report_type": "hr",
      "period_start": "2022-04-01",
      "period_end": "2022-09-30",
      "status": "in_progress",
      "url": null
    }
  ]
}
```

## POST /compliance/reports
Creates a new compliance report.

### Request Body
```json
{
  "entity_id": "entity_abc",
  "report_type": "financial",
  "period_start": "2023-01-01",
  "period_end": "2023-12-31"
}
```

### Response
```json
{
  "id": "report_789",
  "entity_id": "entity_abc",
  "report_type": "financial",
  "period_start": "2023-01-01",
  "period_end": "2023-12-31",
  "status": "in_progress",
  "url": null
}
```

## GET /compliance/reports/{id}
Retrieves a specific compliance report by ID.

### Parameters
| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| `id` | string | The ID of the report to retrieve | Yes |

### Response
```json
{
  "id": "report_123",
  "entity_id": "entity_abc",
  "report_type": "financial",
  "period_start": "2022-01-01",
  "period_end": "2022-12-31",
  "status": "completed",
  "url": "https://example.com/report_123.pdf"
}
```

## PUT /compliance/reports/{id}
Updates an existing compliance report.

### Parameters
| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| `id` | string | The ID of the report to update | Yes |

### Request Body
```json
{
  "status": "completed",
  "url": "https://example.com/report_123.pdf"
}
```

### Response
```json
{
  "id": "report_123",
  "entity_id": "entity_abc",
  "report_type": "financial",
  "period_start": "2022-01-01",
  "period_end": "2022-12-31",
  "status": "completed",
  "url": "https://example.com/report_123.pdf"
}
```

## DELETE /compliance/reports/{id}
Deletes a specific compliance report.

### Parameters
| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| `id` | string | The ID of the report to delete | Yes |

### Response
```json
{
  "message": "Report deleted successfully"
}
```

### Error Codes
| Status Code | Description |
| ----------- | ----------- |
| 400 | Bad request (e.g., missing required parameters) |
| 404 | Report not found |
| 500 | Internal server error |