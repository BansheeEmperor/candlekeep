---
title: Inventory Management API
description: API for managing inventory of products in an e-commerce store.
keywords: [inventory, products, stock, management, e-commerce]
category: api-reference
---

## Get All Products

### GET /products

Retrieve a list of all products in the inventory.

### Parameters

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| page | integer | The page number to retrieve (default: 1) | No |
| limit | integer | The number of results to return per page (default: 25) | No |
| search | string | Search query to filter products | No |

### Response

```json
{
  "data": [
    {
      "id": 1,
      "name": "Product A",
      "description": "This is a description of Product A",
      "price": 19.99,
      "stock": 50
    },
    {
      "id": 2,
      "name": "Product B",
      "description": "This is a description of Product B",
      "price": 29.99,
      "stock": 25
    }
  ],
  "meta": {
    "total": 100,
    "page": 1,
    "limit": 25
  }
}
```

## Get Product Details

### GET /products/{id}

Retrieve details of a specific product.

### Parameters

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| id | integer | The ID of the product to retrieve | Yes |

### Response

```json
{
  "data": {
    "id": 1,
    "name": "Product A",
    "description": "This is a description of Product A",
    "price": 19.99,
    "stock": 50,
    "created_at": "2023-04-01T12:00:00Z",
    "updated_at": "2023-04-05T15:30:00Z"
  }
}
```

## Create a New Product

### POST /products

Create a new product in the inventory.

### Request Body

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| name | string | The name of the product | Yes |
| description | string | The description of the product | Yes |
| price | number | The price of the product | Yes |
| stock | integer | The initial stock level of the product | Yes |

### Response

```json
{
  "data": {
    "id": 3,
    "name": "Product C",
    "description": "This is a description of Product C",
    "price": 14.99,
    "stock": 75,
    "created_at": "2023-04-10T09:45:00Z",
    "updated_at": "2023-04-10T09:45:00Z"
  }
}
```

## Update a Product

### PUT /products/{id}

Update the details of an existing product.

### Parameters

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| id | integer | The ID of the product to update | Yes |

### Request Body

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| name | string | The new name of the product | No |
| description | string | The new description of the product | No |
| price | number | The new price of the product | No |
| stock | integer | The new stock level of the product | No |

### Response

```json
{
  "data": {
    "id": 1,
    "name": "Updated Product A",
    "description": "This is an updated description of Product A",
    "price": 24.99,
    "stock": 60,
    "created_at": "2023-04-01T12:00:00Z",
    "updated_at": "2023-04-11T16:20:00Z"
  }
}
```

## Delete a Product

### DELETE /products/{id}

Delete a product from the inventory.

### Parameters

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| id | integer | The ID of the product to delete | Yes |

### Response

```json
{
  "data": {
    "id": 2,
    "name": "Product B",
    "description": "This is a description of Product B",
    "price": 29.99,
    "stock": 25,
    "created_at": "2023-04-05T10:30:00Z",
    "updated_at": "2023-04-08T14:15:00Z"
  }
}
```

## Error Codes

| Status Code | Description |
| ----------- | ----------- |
| 400 | Bad Request - The request is invalid or missing required parameters. |
| 404 | Not Found - The requested resource was not found. |
| 500 | Internal Server Error - An unexpected error occurred on the server. |