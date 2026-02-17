---
title: Payment Processing API
description: Securely process online payments with our robust API.
keywords: [payment, processing, transactions, credit card, ecommerce]
category: api-reference
---

## POST /payments
Process a new payment transaction.

### Parameters
| Name | Type | Required | Description |
| --- | --- | --- | --- |
| amount | number | Yes | The total amount to charge, in the specified currency. |
| currency | string | Yes | The 3-letter ISO 4217 currency code. |
| card_number | string | Yes | The credit/debit card number. |
| expiry_month | integer | Yes | The expiry month of the card (1-12). |
| expiry_year | integer | Yes | The expiry year of the card (YYYY). |
| cvv | string | Yes | The 3-digit security code on the back of the card. |
| customer_name | string | Yes | The name of the card holder. |
| customer_email | string | Yes | The email address of the customer. |
| customer_address1 | string | No | The first line of the customer's billing address. |
| customer_address2 | string | No | The second line of the customer's billing address. |
| customer_city | string | No | The city of the customer's billing address. |
| customer_state | string | No | The state/province of the customer's billing address. |
| customer_zip | string | No | The zip/postal code of the customer's billing address. |
| customer_country | string | No | The country of the customer's billing address. |

### Request Body
```json
{
  "amount": 99.99,
  "currency": "USD",
  "card_number": "4111111111111111",
  "expiry_month": 12,
  "expiry_year": 2025,
  "cvv": "123",
  "customer_name": "John Doe",
  "customer_email": "john.doe@example.com",
  "customer_address1": "123 Main St",
  "customer_city": "Anytown",
  "customer_state": "CA",
  "customer_zip": "12345",
  "customer_country": "US"
}
```

### Response
```json
{
  "id": "tx_1234567890",
  "amount": 99.99,
  "currency": "USD",
  "status": "successful",
  "created_at": "2023-04-01T12:34:56Z"
}
```

### Error Codes
| Status Code | Description |
| --- | --- |
| 400 | Invalid request parameters |
| 401 | Unauthorized access |
| 402 | Payment required |
| 500 | Internal server error |

## GET /payments/{id}
Retrieve details of a specific payment transaction.

### Parameters
| Name | Type | Required | Description |
| --- | --- | --- | --- |
| id | string | Yes | The unique identifier of the payment transaction. |

### Response
```json
{
  "id": "tx_1234567890",
  "amount": 99.99,
  "currency": "USD",
  "status": "successful",
  "created_at": "2023-04-01T12:34:56Z",
  "customer_name": "John Doe",
  "customer_email": "john.doe@example.com",
  "customer_address1": "123 Main St",
  "customer_city": "Anytown",
  "customer_state": "CA",
  "customer_zip": "12345",
  "customer_country": "US"
}
```

### Error Codes
| Status Code | Description |
| --- | --- |
| 404 | Payment transaction not found |
| 500 | Internal server error |

## GET /payments
Retrieve a list of payment transactions.

### Parameters
| Name | Type | Required | Description |
| --- | --- | --- | --- |
| page | integer | No | The page number to retrieve (default: 1). |
| limit | integer | No | The number of results to return per page (default: 20, max: 100). |
| status | string | No | Filter transactions by status (e.g., "successful", "failed"). |
| created_at_min | string | No | Filter transactions created on or after the specified date (YYYY-MM-DD). |
| created_at_max | string | No | Filter transactions created on or before the specified date (YYYY-MM-DD). |

### Response
```json
{
  "data": [
    {
      "id": "tx_1234567890",
      "amount": 99.99,
      "currency": "USD",
      "status": "successful",
      "created_at": "2023-04-01T12:34:56Z"
    },
    {
      "id": "tx_0987654321",
      "amount": 49.99,
      "currency": "USD",
      "status": "failed",
      "created_at": "2023-03-31T15:23:45Z"
    }
  ],
  "pagination": {
    "current_page": 1,
    "total_pages": 10,
    "total_records": 200
  }
}
```

### Error Codes
| Status Code | Description |
| --- | --- |
| 500 | Internal server error |

## DELETE /payments/{id}
Cancel a payment transaction.

### Parameters
| Name | Type | Required | Description |
| --- | --- | --- | --- |
| id | string | Yes | The unique identifier of the payment transaction. |

### Response
```json
{
  "id": "tx_1234567890",
  "amount": 99.99,
  "currency": "USD",
  "status": "cancelled",
  "created_at": "2023-04-01T12:34:56Z"
}
```

### Error Codes
| Status Code | Description |
| --- | --- |
| 404 | Payment transaction not found |
| 500 | Internal server error |