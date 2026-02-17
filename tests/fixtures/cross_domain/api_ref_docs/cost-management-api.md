---
title: Cost Management API
description: Manage organization-wide cost data and budgets
keywords: [cost, budget, finance, reporting, analytics]
category: api-reference
---

## GET /costs
Retrieve a list of costs incurred by the organization.

### Parameters

| Name | Type | Description | Required |
| --- | --- | --- | --- |
| start_date | date | The start date for the cost data (YYYY-MM-DD) | Yes |
| end_date | date | The end date for the cost data (YYYY-MM-DD) | Yes |
| department | string | Filter costs by department | No |
| project | string | Filter costs by project | No |

### Response

```json
[
  {
    "id": "c123456",
    "date": "2023-04-01",
    "department": "Marketing",
    "project": "Brand Campaign",
    "category": "Advertising",
    "amount": 5000.00,
    "description": "Facebook ad spend"
  },
  {
    "id": "c234567",
    "date": "2023-04-05",
    "department": "IT",
    "project": "Server Upgrade",
    "category": "Hardware",
    "amount": 2500.00,
    "description": "New server purchase"
  }
]
```

### Error Codes

| Code | Description |
| --- | --- |
| 400 | Invalid request parameters |
| 403 | Forbidden: user does not have permission to access costs |
| 500 | Internal server error |

## POST /budgets
Create a new budget for the organization.

### Request Body

```json
{
  "name": "Q2 Marketing Budget",
  "department": "Marketing",
  "project": "Brand Campaign",
  "category": "Advertising",
  "amount": 50000.00,
  "start_date": "2023-04-01",
  "end_date": "2023-06-30"
}
```

### Response

```json
{
  "id": "b123456",
  "name": "Q2 Marketing Budget",
  "department": "Marketing",
  "project": "Brand Campaign",
  "category": "Advertising",
  "amount": 50000.00,
  "start_date": "2023-04-01",
  "end_date": "2023-06-30"
}
```

### Error Codes

| Code | Description |
| --- | --- |
| 400 | Invalid request body |
| 403 | Forbidden: user does not have permission to create budgets |
| 409 | Conflict: budget with the same name already exists |
| 500 | Internal server error |

## GET /budgets
Retrieve a list of budgets for the organization.

### Parameters

| Name | Type | Description | Required |
| --- | --- | --- | --- |
| department | string | Filter budgets by department | No |
| project | string | Filter budgets by project | No |
| category | string | Filter budgets by category | No |

### Response

```json
[
  {
    "id": "b123456",
    "name": "Q2 Marketing Budget",
    "department": "Marketing",
    "project": "Brand Campaign",
    "category": "Advertising",
    "amount": 50000.00,
    "start_date": "2023-04-01",
    "end_date": "2023-06-30"
  },
  {
    "id": "b234567",
    "name": "IT Infrastructure Budget",
    "department": "IT",
    "project": "Server Upgrade",
    "category": "Hardware",
    "amount": 25000.00,
    "start_date": "2023-01-01",
    "end_date": "2023-12-31"
  }
]
```

### Error Codes

| Code | Description |
| --- | --- |
| 403 | Forbidden: user does not have permission to view budgets |
| 500 | Internal server error |

## PATCH /budgets/{id}
Update an existing budget.

### Parameters

| Name | Type | Description | Required |
| --- | --- | --- | --- |
| id | string | The ID of the budget to update | Yes |

### Request Body

```json
{
  "name": "Q2 Marketing Budget (Updated)",
  "amount": 55000.00
}
```

### Response

```json
{
  "id": "b123456",
  "name": "Q2 Marketing Budget (Updated)",
  "department": "Marketing",
  "project": "Brand Campaign",
  "category": "Advertising",
  "amount": 55000.00,
  "start_date": "2023-04-01",
  "end_date": "2023-06-30"
}
```

### Error Codes

| Code | Description |
| --- | --- |
| 400 | Invalid request body |
| 403 | Forbidden: user does not have permission to update budgets |
| 404 | Not found: budget with the specified ID does not exist |
| 500 | Internal server error |