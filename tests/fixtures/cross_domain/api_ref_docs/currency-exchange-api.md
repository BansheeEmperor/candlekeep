---
title: Currency Exchange API
description: Retrieve up-to-date exchange rates for major world currencies.
keywords: [currency, exchange, rates, forex, finance, money]
category: api-reference
---

## Get Exchange Rates

### GET /api/v1/exchange_rates

Retrieve the latest exchange rates for a specified base currency.

#### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| base | string | Yes | The base currency to use for the exchange rates. |
| symbols | string | No | A comma-separated list of currency codes to retrieve rates for. If not provided, all rates will be returned. |

#### Response

```json
{
  "base": "USD",
  "date": "2023-04-19",
  "rates": {
    "EUR": 0.9123,
    "GBP": 0.8045,
    "JPY": 134.56,
    "CAD": 1.3456,
    "AUD": 1.5123
  }
}
```

#### Error Codes

| Status Code | Description |
| --- | --- |
| 400 | Invalid base currency or symbols provided. |
| 404 | Exchange rates not found for the specified parameters. |
| 500 | Internal server error. |

## Convert Currency

### POST /api/v1/convert

Convert an amount from one currency to another.

#### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| amount | number | Yes | The amount to be converted. |
| from | string | Yes | The currency code to convert from. |
| to | string | Yes | The currency code to convert to. |

#### Request Body

```json
{
  "amount": 100.00,
  "from": "USD",
  "to": "EUR"
}
```

#### Response

```json
{
  "amount": 91.23,
  "from": "USD",
  "to": "EUR",
  "rate": 0.9123,
  "date": "2023-04-19"
}
```

#### Error Codes

| Status Code | Description |
| --- | --- |
| 400 | Invalid input parameters. |
| 404 | No exchange rate found for the specified currencies. |
| 500 | Internal server error. |

## Historical Exchange Rates

### GET /api/v1/historical_rates

Retrieve historical exchange rates for a specified date range and currencies.

#### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| base | string | Yes | The base currency to use for the exchange rates. |
| symbols | string | No | A comma-separated list of currency codes to retrieve rates for. If not provided, all rates will be returned. |
| start_date | string | Yes | The start date for the historical data in the format YYYY-MM-DD. |
| end_date | string | Yes | The end date for the historical data in the format YYYY-MM-DD. |

#### Response

```json
{
  "base": "USD",
  "start_date": "2023-04-01",
  "end_date": "2023-04-19",
  "rates": [
    {
      "date": "2023-04-01",
      "rates": {
        "EUR": 0.9234,
        "GBP": 0.8123,
        "JPY": 132.45
      }
    },
    {
      "date": "2023-04-02",
      "rates": {
        "EUR": 0.9256,
        "GBP": 0.8145,
        "JPY": 133.12
      }
    },
    {
      "date": "2023-04-03",
      "rates": {
        "EUR": 0.9267,
        "GBP": 0.8167,
        "JPY": 133.89
      }
    }
  ]
}
```

#### Error Codes

| Status Code | Description |
| --- | --- |
| 400 | Invalid base currency, symbols, or date range provided. |
| 404 | Historical exchange rates not found for the specified parameters. |
| 500 | Internal server error. |

## List Supported Currencies

### GET /api/v1/currencies

Retrieve a list of all currencies supported by the API.

#### Response

```json
{
  "currencies": [
    "USD",
    "EUR",
    "GBP",
    "JPY",
    "CAD",
    "AUD",
    "CHF",
    "CNY",
    "HKD",
    "NZD"
  ]
}
```

#### Error Codes

| Status Code | Description |
| --- | --- |
| 500 | Internal server error. |