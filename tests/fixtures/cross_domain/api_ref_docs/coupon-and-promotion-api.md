---
title: Coupon and Promotion API
description: API for managing coupons and promotions in an e-commerce platform.
keywords: [coupons, promotions, discounts, ecommerce, marketing]
category: api-reference
---

## List Coupons
`GET /api/coupons`

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| status | string | No | Filter coupons by status (active, expired, disabled) |
| code | string | No | Filter coupons by code |
| page | integer | No | Page number for pagination |
| limit | integer | No | Number of results per page |

### Response

```json
{
  "data": [
    {
      "id": "123456",
      "code": "SUMMERSALE",
      "type": "percentage",
      "value": 20,
      "start_date": "2023-06-01",
      "end_date": "2023-08-31",
      "status": "active"
    },
    {
      "id": "789012",
      "code": "NEWCUSTOMER",
      "type": "fixed_amount",
      "value": 10,
      "start_date": "2023-01-01",
      "end_date": "2023-12-31",
      "status": "active"
    }
  ],
  "meta": {
    "total_count": 25,
    "page": 1,
    "limit": 10
  }
}
```

## Create Coupon
`POST /api/coupons`

### Request Body

```json
{
  "code": "SUMMERSALE",
  "type": "percentage",
  "value": 20,
  "start_date": "2023-06-01",
  "end_date": "2023-08-31",
  "status": "active"
}
```

### Response

```json
{
  "id": "123456",
  "code": "SUMMERSALE",
  "type": "percentage",
  "value": 20,
  "start_date": "2023-06-01",
  "end_date": "2023-08-31",
  "status": "active"
}
```

## Update Coupon
`PUT /api/coupons/{id}`

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| id | string | Yes | ID of the coupon to update |

### Request Body

```json
{
  "code": "SUMMERSALE2",
  "type": "percentage",
  "value": 25,
  "start_date": "2023-06-01",
  "end_date": "2023-09-30",
  "status": "active"
}
```

### Response

```json
{
  "id": "123456",
  "code": "SUMMERSALE2",
  "type": "percentage",
  "value": 25,
  "start_date": "2023-06-01",
  "end_date": "2023-09-30",
  "status": "active"
}
```

## Delete Coupon
`DELETE /api/coupons/{id}`

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| id | string | Yes | ID of the coupon to delete |

### Response

```json
{
  "message": "Coupon deleted successfully"
}
```

## List Promotions
`GET /api/promotions`

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| status | string | No | Filter promotions by status (active, expired, disabled) |
| name | string | No | Filter promotions by name |
| page | integer | No | Page number for pagination |
| limit | integer | No | Number of results per page |

### Response

```json
{
  "data": [
    {
      "id": "987654",
      "name": "Summer Sale",
      "type": "percentage",
      "value": 20,
      "start_date": "2023-06-01",
      "end_date": "2023-08-31",
      "status": "active"
    },
    {
      "id": "456789",
      "name": "New Customer Discount",
      "type": "fixed_amount",
      "value": 10,
      "start_date": "2023-01-01",
      "end_date": "2023-12-31",
      "status": "active"
    }
  ],
  "meta": {
    "total_count": 15,
    "page": 1,
    "limit": 10
  }
}
```

## Error Codes

| Code | Description |
| --- | --- |
| 400 | Bad Request - Invalid input data |
| 404 | Not Found - Requested resource not found |
| 409 | Conflict - Duplicate coupon/promotion code |
| 500 | Internal Server Error - Something went wrong on the server |