---
title: Subscription Billing API
description: API for managing subscription-based billing and payments
keywords: [subscription, billing, payments, SaaS, recurring]
category: api-reference
---

## Get Subscriptions
`GET /subscriptions`

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `customer_id` | string | true | ID of the customer |
| `status` | string | false | Filter by subscription status (active, cancelled, etc.) |

### Response

```json
[
  {
    "id": "sub_123abc",
    "customer_id": "cust_456def",
    "plan_id": "plan_789ghi",
    "status": "active",
    "start_date": "2022-01-01",
    "end_date": "2023-01-01",
    "renewal_frequency": "monthly",
    "next_billing_date": "2022-02-01",
    "total_amount": 9.99,
    "currency": "USD"
  },
  {
    "id": "sub_987jkl",
    "customer_id": "cust_456def",
    "plan_id": "plan_012mno",
    "status": "cancelled",
    "start_date": "2021-06-15",
    "end_date": "2022-06-15",
    "renewal_frequency": "yearly",
    "next_billing_date": null,
    "total_amount": 99.99,
    "currency": "USD"
  }
]
```

## Create Subscription
`POST /subscriptions`

### Request Body

```json
{
  "customer_id": "cust_456def",
  "plan_id": "plan_789ghi",
  "start_date": "2022-01-01",
  "renewal_frequency": "monthly",
  "payment_method_id": "pm_123abc"
}
```

### Response

```json
{
  "id": "sub_123abc",
  "customer_id": "cust_456def",
  "plan_id": "plan_789ghi",
  "status": "active",
  "start_date": "2022-01-01",
  "end_date": "2023-01-01",
  "renewal_frequency": "monthly",
  "next_billing_date": "2022-02-01",
  "total_amount": 9.99,
  "currency": "USD"
}
```

## Update Subscription
`PATCH /subscriptions/{id}`

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | string | true | ID of the subscription to update |

### Request Body

```json
{
  "status": "cancelled",
  "end_date": "2022-06-15"
}
```

### Response

```json
{
  "id": "sub_123abc",
  "customer_id": "cust_456def",
  "plan_id": "plan_789ghi",
  "status": "cancelled",
  "start_date": "2022-01-01",
  "end_date": "2022-06-15",
  "renewal_frequency": "monthly",
  "next_billing_date": null,
  "total_amount": 9.99,
  "currency": "USD"
}
```

## Cancel Subscription
`DELETE /subscriptions/{id}`

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | string | true | ID of the subscription to cancel |

### Response

```json
{
  "id": "sub_123abc",
  "customer_id": "cust_456def",
  "plan_id": "plan_789ghi",
  "status": "cancelled",
  "start_date": "2022-01-01",
  "end_date": "2022-06-15",
  "renewal_frequency": "monthly",
  "next_billing_date": null,
  "total_amount": 9.99,
  "currency": "USD"
}
```

## Error Codes

| Code | Description |
| --- | --- |
| 400 | Bad Request - Invalid input data |
| 401 | Unauthorized - Invalid API key |
| 404 | Not Found - Requested resource not found |
| 409 | Conflict - Subscription status conflict (e.g., attempting to cancel an already cancelled subscription) |
| 500 | Internal Server Error - Unexpected server error |