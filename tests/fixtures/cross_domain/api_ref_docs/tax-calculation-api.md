---
title: Tax Calculation API
description: Compute taxes for sales transactions
keywords: [tax, sales, calculation, transaction, finance]
category: api-reference
---

## GET /taxes

Retrieve tax rates for a given location.

### Parameters

| Name | Type | Description |
| --- | --- | --- |
| `country` | string | The country code (ISO 3166-1 alpha-2) |
| `state` | string | The state or region code (ISO 3166-2) |
| `city` | string | The city name |
| `zip_code` | string | The postal code |

### Response

```json
{
  "country_tax_rate": 0.07,
  "state_tax_rate": 0.045,
  "city_tax_rate": 0.02,
  "total_tax_rate": 0.115
}
```

## POST /calculate

Calculate the total tax amount for a sales transaction.

### Request Body

```json
{
  "subtotal": 100.00,
  "country": "US",
  "state": "CA",
  "city": "San Francisco",
  "zip_code": "94102"
}
```

### Response

```json
{
  "subtotal": 100.00,
  "country_tax": 7.00,
  "state_tax": 4.50,
  "city_tax": 2.00,
  "total_tax": 13.50,
  "total_amount": 113.50
}
```

### Error Codes

| Status Code | Description |
| --- | --- |
| 400 | Invalid request parameters |
| 404 | Tax rates not found for the given location |
| 500 | Internal server error |

## GET /rates/history

Retrieve historical tax rate changes for a given location.

### Parameters

| Name | Type | Description |
| --- | --- | --- |
| `country` | string | The country code (ISO 3166-1 alpha-2) |
| `state` | string | The state or region code (ISO 3166-2) |
| `city` | string | The city name |
| `zip_code` | string | The postal code |
| `start_date` | string | The start date of the historical period (YYYY-MM-DD) |
| `end_date` | string | The end date of the historical period (YYYY-MM-DD) |

### Response

```json
[
  {
    "effective_date": "2022-01-01",
    "country_tax_rate": 0.07,
    "state_tax_rate": 0.045,
    "city_tax_rate": 0.02,
    "total_tax_rate": 0.115
  },
  {
    "effective_date": "2021-07-01",
    "country_tax_rate": 0.07,
    "state_tax_rate": 0.045,
    "city_tax_rate": 0.018,
    "total_tax_rate": 0.113
  },
  {
    "effective_date": "2020-01-01",
    "country_tax_rate": 0.07,
    "state_tax_rate": 0.045,
    "city_tax_rate": 0.016,
    "total_tax_rate": 0.111
  }
]
```

### Error Codes

| Status Code | Description |
| --- | --- |
| 400 | Invalid request parameters |
| 404 | No historical tax rate data found for the given location and time period |
| 500 | Internal server error |

## POST /validate

Validate a sales transaction and return the calculated taxes.

### Request Body

```json
{
  "subtotal": 100.00,
  "country": "US",
  "state": "CA",
  "city": "San Francisco",
  "zip_code": "94102"
}
```

### Response

```json
{
  "is_valid": true,
  "subtotal": 100.00,
  "country_tax": 7.00,
  "state_tax": 4.50,
  "city_tax": 2.00,
  "total_tax": 13.50,
  "total_amount": 113.50
}
```

### Error Codes

| Status Code | Description |
| --- | --- |
| 400 | Invalid request parameters |
| 404 | Tax rates not found for the given location |
| 500 | Internal server error |