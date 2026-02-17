---
title: Shipping and Logistics API
description: A RESTful API for managing shipping and logistics operations.
keywords: [shipping, logistics, delivery, tracking, inventory]
category: api-reference
---

## GET /shipments
Retrieve a list of shipments.

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| status | string | Filter shipments by status (e.g., "pending", "shipped", "delivered") | No |
| page | integer | Page number for pagination | No |
| limit | integer | Number of results per page | No |

### Response
```json
{
  "data": [
    {
      "id": "123456789",
      "tracking_number": "1Z999AA1205904321",
      "status": "shipped",
      "carrier": "UPS",
      "origin": "New York, NY",
      "destination": "Los Angeles, CA",
      "created_at": "2023-04-01T12:00:00Z",
      "updated_at": "2023-04-03T15:30:00Z"
    },
    {
      "id": "987654321",
      "tracking_number": "1Z123AB1234567890",
      "status": "delivered",
      "carrier": "FedEx",
      "origin": "Chicago, IL",
      "destination": "Seattle, WA",
      "created_at": "2023-03-28T09:15:00Z",
      "updated_at": "2023-03-30T14:20:00Z"
    }
  ],
  "meta": {
    "total": 50,
    "page": 1,
    "limit": 2
  }
}
```

## POST /shipments
Create a new shipment.

### Request Body
```json
{
  "tracking_number": "1Z999AA1205904321",
  "carrier": "UPS",
  "origin": {
    "address1": "123 Main St",
    "city": "New York",
    "state": "NY",
    "zip": "10001"
  },
  "destination": {
    "address1": "456 Oak Rd",
    "city": "Los Angeles",
    "state": "CA",
    "zip": "90001"
  },
  "items": [
    {
      "name": "Product A",
      "quantity": 2,
      "weight": 5.0
    },
    {
      "name": "Product B",
      "quantity": 1,
      "weight": 3.5
    }
  ]
}
```

### Response
```json
{
  "id": "123456789",
  "tracking_number": "1Z999AA1205904321",
  "status": "pending",
  "carrier": "UPS",
  "origin": {
    "address1": "123 Main St",
    "city": "New York",
    "state": "NY",
    "zip": "10001"
  },
  "destination": {
    "address1": "456 Oak Rd",
    "city": "Los Angeles",
    "state": "CA",
    "zip": "90001"
  },
  "items": [
    {
      "name": "Product A",
      "quantity": 2,
      "weight": 5.0
    },
    {
      "name": "Product B",
      "quantity": 1,
      "weight": 3.5
    }
  ],
  "created_at": "2023-04-01T12:00:00Z",
  "updated_at": "2023-04-01T12:00:00Z"
}
```

## GET /shipments/{id}
Retrieve a specific shipment.

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| id | string | The ID of the shipment | Yes |

### Response
```json
{
  "id": "123456789",
  "tracking_number": "1Z999AA1205904321",
  "status": "shipped",
  "carrier": "UPS",
  "origin": {
    "address1": "123 Main St",
    "city": "New York",
    "state": "NY",
    "zip": "10001"
  },
  "destination": {
    "address1": "456 Oak Rd",
    "city": "Los Angeles",
    "state": "CA",
    "zip": "90001"
  },
  "items": [
    {
      "name": "Product A",
      "quantity": 2,
      "weight": 5.0
    },
    {
      "name": "Product B",
      "quantity": 1,
      "weight": 3.5
    }
  ],
  "created_at": "2023-04-01T12:00:00Z",
  "updated_at": "2023-04-03T15:30:00Z"
}
```

## PATCH /shipments/{id}
Update a specific shipment.

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| id | string | The ID of the shipment | Yes |

### Request Body
```json
{
  "status": "delivered",
  "delivered_at": "2023-04-05T10:45:00Z"
}
```

### Response
```json
{
  "id": "123456789",
  "tracking_number": "1Z999AA1205904321",
  "status": "delivered",
  "carrier": "UPS",
  "origin": {
    "address1": "123 Main St",
    "city": "New York",
    "state": "NY",
    "zip": "10001"
  },
  "destination": {
    "address1": "456 Oak Rd",
    "city": "Los Angeles",
    "state": "CA",
    "zip": "90001"
  },
  "items": [
    {
      "name": "Product A",
      "quantity": 2,
      "weight": 5.0
    },
    {
      "name": "Product B",
      "quantity": 1,
      "weight": 3.5
    }
  ],
  "created_at": "2023-04-01T12:00:00Z",
  "updated_at": "2023-04-05T10:45:00Z",
  "delivered_at": "2023-04-05T10:45:00Z"
}
```

## Error Codes
| HTTP Status | Error Code | Description |
| --- | --- | --- |
| 400 | INVALID_REQUEST | The request is invalid or missing required parameters. |
| 404 | NOT_FOUND | The requested resource was not found. |
| 500 | INTERNAL_SERVER_ERROR | An unexpected error occurred on the server. |