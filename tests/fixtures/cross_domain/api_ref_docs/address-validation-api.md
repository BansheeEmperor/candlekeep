---
title: Address Validation API
description: Validate and standardize addresses using a robust address database.
keywords: [address, validation, standardization, geocoding, location]
category: api-reference
---

## `GET /validate`
Validate and standardize an address.

### Parameters
| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `street` | `string` | Yes | The street address. |
| `city` | `string` | Yes | The city. |
| `state` | `string` | Yes | The state or province. |
| `zip` | `string` | Yes | The postal code. |
| `country` | `string` | Yes | The country. |

### Response
```json
{
  "validated_address": {
    "street": "123 Main St",
    "city": "Anytown",
    "state": "CA",
    "zip": "12345",
    "country": "USA"
  },
  "latitude": 38.9072,
  "longitude": -77.0369,
  "accuracy_score": 0.95
}
```

### Error Codes
| Status Code | Description |
| --- | --- |
| 400 | Invalid request parameters. |
| 404 | Address not found. |
| 500 | Internal server error. |

## `POST /batch`
Validate and standardize a batch of addresses.

### Request Body
```json
[
  {
    "street": "123 Main St",
    "city": "Anytown",
    "state": "CA",
    "zip": "12345",
    "country": "USA"
  },
  {
    "street": "456 Oak Rd",
    "city": "Othertown",
    "state": "NY",
    "zip": "54321",
    "country": "USA"
  }
]
```

### Response
```json
[
  {
    "validated_address": {
      "street": "123 Main St",
      "city": "Anytown",
      "state": "CA",
      "zip": "12345",
      "country": "USA"
    },
    "latitude": 38.9072,
    "longitude": -77.0369,
    "accuracy_score": 0.95
  },
  {
    "validated_address": {
      "street": "456 Oak Rd",
      "city": "Othertown",
      "state": "NY",
      "zip": "54321",
      "country": "USA"
    },
    "latitude": 40.7128,
    "longitude": -74.0060,
    "accuracy_score": 0.92
  }
]
```

### Error Codes
| Status Code | Description |
| --- | --- |
| 400 | Invalid request body. |
| 404 | One or more addresses not found. |
| 500 | Internal server error. |

## `GET /autocomplete`
Autocomplete an address based on partial input.

### Parameters
| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `query` | `string` | Yes | The partial address to autocomplete. |
| `limit` | `integer` | No | The maximum number of results to return (default is 10). |

### Response
```json
[
  {
    "street": "123 Main St",
    "city": "Anytown",
    "state": "CA",
    "zip": "12345",
    "country": "USA"
  },
  {
    "street": "456 Oak Rd",
    "city": "Othertown",
    "state": "CA",
    "zip": "54321",
    "country": "USA"
  },
  {
    "street": "789 Elm Blvd",
    "city": "Thirdtown",
    "state": "CA",
    "zip": "67890",
    "country": "USA"
  }
]
```

### Error Codes
| Status Code | Description |
| --- | --- |
| 400 | Invalid request parameters. |
| 500 | Internal server error. |

## `GET /geocode`
Geocode an address to retrieve latitude and longitude coordinates.

### Parameters
| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `street` | `string` | Yes | The street address. |
| `city` | `string` | Yes | The city. |
| `state` | `string` | Yes | The state or province. |
| `zip` | `string` | Yes | The postal code. |
| `country` | `string` | Yes | The country. |

### Response
```json
{
  "latitude": 38.9072,
  "longitude": -77.0369
}
```

### Error Codes
| Status Code | Description |
| --- | --- |
| 400 | Invalid request parameters. |
| 404 | Address not found. |
| 500 | Internal server error. |