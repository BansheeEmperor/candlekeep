---
title: Budget Alert API
description: Manage budget alerts for your financial accounts
keywords: [budget, alerts, finance, accounts, notifications]
category: api-reference
---

## GET /budgets

Retrieve a list of all budgets associated with the authenticated user.

### Parameters

| Name | Type | Description | Required |
| --- | --- | --- | --- |
| `page` | integer | The page number to retrieve (default: 1) | No |
| `limit` | integer | The number of results to return per page (default: 10) | No |

### Response

```json
{
  "data": [
    {
      "id": "123456",
      "name": "Rent",
      "amount": 1000,
      "category": "Housing",
      "created_at": "2023-04-01T12:00:00Z",
      "updated_at": "2023-04-01T12:00:00Z"
    },
    {
      "id": "789012",
      "name": "Groceries",
      "amount": 500,
      "category": "Food",
      "created_at": "2023-04-01T12:00:00Z",
      "updated_at": "2023-04-01T12:00:00Z"
    }
  ],
  "meta": {
    "total": 2,
    "page": 1,
    "limit": 10
  }
}
```

## POST /budgets

Create a new budget.

### Request Body

```json
{
  "name": "Utilities",
  "amount": 200,
  "category": "Bills"
}
```

### Response

```json
{
  "data": {
    "id": "345678",
    "name": "Utilities",
    "amount": 200,
    "category": "Bills",
    "created_at": "2023-04-01T12:00:00Z",
    "updated_at": "2023-04-01T12:00:00Z"
  }
}
```

## GET /budgets/{id}

Retrieve a specific budget.

### Parameters

| Name | Type | Description | Required |
| --- | --- | --- | --- |
| `id` | string | The ID of the budget to retrieve | Yes |

### Response

```json
{
  "data": {
    "id": "123456",
    "name": "Rent",
    "amount": 1000,
    "category": "Housing",
    "created_at": "2023-04-01T12:00:00Z",
    "updated_at": "2023-04-01T12:00:00Z"
  }
}
```

## PATCH /budgets/{id}

Update an existing budget.

### Parameters

| Name | Type | Description | Required |
| --- | --- | --- | --- |
| `id` | string | The ID of the budget to update | Yes |

### Request Body

```json
{
  "name": "Rent (Updated)",
  "amount": 1100,
  "category": "Housing"
}
```

### Response

```json
{
  "data": {
    "id": "123456",
    "name": "Rent (Updated)",
    "amount": 1100,
    "category": "Housing",
    "created_at": "2023-04-01T12:00:00Z",
    "updated_at": "2023-04-02T12:00:00Z"
  }
}
```

## DELETE /budgets/{id}

Delete a specific budget.

### Parameters

| Name | Type | Description | Required |
| --- | --- | --- | --- |
| `id` | string | The ID of the budget to delete | Yes |

### Response

```json
{
  "data": {
    "id": "123456",
    "name": "Rent (Updated)",
    "amount": 1100,
    "category": "Housing",
    "created_at": "2023-04-01T12:00:00Z",
    "updated_at": "2023-04-02T12:00:00Z"
  }
}
```

## Error Codes

| Status Code | Description |
| --- | --- |
| 400 Bad Request | The request was malformed or invalid. |
| 401 Unauthorized | The request requires authentication. |
| 404 Not Found | The requested resource was not found. |
| 500 Internal Server Error | An unexpected error occurred on the server. |