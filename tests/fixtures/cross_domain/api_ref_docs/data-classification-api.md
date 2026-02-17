---
title: Data Classification API
description: An API for classifying data into predefined categories.
keywords: [data classification, machine learning, AI, API, text analysis]
category: api-reference
---

## `POST /classify`

Classify the provided text or data into one or more predefined categories.

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `text` | `string` | Yes | The text or data to be classified. |
| `categories` | `array[string]` | No | An optional list of category names to limit the classification to. If not provided, the API will classify the input into all available categories. |

### Request Body

```json
{
  "text": "This is a sample text that needs to be classified.",
  "categories": ["business", "technology", "entertainment"]
}
```

### Response

```json
{
  "classifications": [
    {
      "category": "business",
      "score": 0.8
    },
    {
      "category": "technology",
      "score": 0.6
    },
    {
      "category": "entertainment",
      "score": 0.3
    }
  ]
}
```

### Error Codes

| Status Code | Error Description |
| --- | --- |
| 400 | `Bad Request` - The request is missing required parameters or the parameters are invalid. |
| 500 | `Internal Server Error` - An unexpected error occurred while processing the request. |

## `GET /categories`

Retrieve a list of all available categories that the API can classify data into.

### Response

```json
{
  "categories": [
    "business",
    "technology",
    "entertainment",
    "sports",
    "politics",
    "health"
  ]
}
```

### Error Codes

| Status Code | Error Description |
| --- | --- |
| 500 | `Internal Server Error` - An unexpected error occurred while retrieving the categories. |

## `POST /train`

Train the classification model with new data and categories.

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `data` | `array[object]` | Yes | An array of objects, where each object contains the `text` and `category` fields. |

### Request Body

```json
{
  "data": [
    {
      "text": "This is a business-related article.",
      "category": "business"
    },
    {
      "text": "The latest technology news.",
      "category": "technology"
    },
    {
      "text": "A review of the new blockbuster movie.",
      "category": "entertainment"
    }
  ]
}
```

### Response

```json
{
  "message": "Model training completed successfully."
}
```

### Error Codes

| Status Code | Error Description |
| --- | --- |
| 400 | `Bad Request` - The request is missing required parameters or the parameters are invalid. |
| 500 | `Internal Server Error` - An unexpected error occurred while training the model. |

## `DELETE /model`

Delete the current classification model and reset the API to its initial state.

### Response

```json
{
  "message": "Model deleted successfully."
}
```

### Error Codes

| Status Code | Error Description |
| --- | --- |
| 500 | `Internal Server Error` - An unexpected error occurred while deleting the model. |