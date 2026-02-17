---
title: Search and Autocomplete API
description: Provides search and autocomplete functionality for your application.
keywords: [search, autocomplete, query, results, suggestions]
category: api-reference
---

## GET /search

Search for items in your database.

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `q` | string | Yes | The search query. |
| `page` | integer | No | The page number to retrieve (default: 1). |
| `limit` | integer | No | The maximum number of results to return per page (default: 10, max: 50). |
| `sort` | string | No | The field to sort the results by (e.g., `name`, `price`, `popularity`). |
| `order` | string | No | The sort order, either `asc` or `desc` (default: `asc`). |

### Response

```json
{
  "total": 100,
  "page": 1,
  "limit": 10,
  "results": [
    {
      "id": "1234",
      "name": "Product A",
      "description": "This is a description of Product A.",
      "price": 19.99,
      "image": "https://example.com/product-a.jpg"
    },
    {
      "id": "5678",
      "name": "Product B",
      "description": "This is a description of Product B.",
      "price": 24.99,
      "image": "https://example.com/product-b.jpg"
    },
    // ... more results
  ]
}
```

### Error Codes

| Code | Description |
| --- | --- |
| 400 | Invalid request parameters. |
| 404 | No results found for the given query. |
| 500 | Internal server error. |

## GET /autocomplete

Get autocomplete suggestions for a search query.

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `q` | string | Yes | The search query. |
| `limit` | integer | No | The maximum number of suggestions to return (default: 10, max: 20). |

### Response

```json
{
  "suggestions": [
    "product a",
    "product b",
    "product c",
    "product d",
    "product e"
  ]
}
```

### Error Codes

| Code | Description |
| --- | --- |
| 400 | Invalid request parameters. |
| 500 | Internal server error. |

## POST /search/suggest

Get search suggestions for a query.

### Request Body

```json
{
  "q": "product"
}
```

### Response

```json
{
  "suggestions": [
    "product a",
    "product b",
    "product c",
    "product d",
    "product e"
  ]
}
```

### Error Codes

| Code | Description |
| --- | --- |
| 400 | Invalid request body. |
| 500 | Internal server error. |

## GET /search/popular

Get the most popular search queries.

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `limit` | integer | No | The maximum number of popular queries to return (default: 10, max: 20). |

### Response

```json
{
  "popular_queries": [
    "product",
    "electronics",
    "clothing",
    "furniture",
    "accessories"
  ]
}
```

### Error Codes

| Code | Description |
| --- | --- |
| 400 | Invalid request parameters. |
| 500 | Internal server error. |