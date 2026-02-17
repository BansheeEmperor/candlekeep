---
title: PDF Generation API
description: An API for generating PDFs from HTML templates and data
keywords: [pdf, generation, html, template, document]
category: api-reference
---

## `POST /pdf`

Generate a PDF document from an HTML template and data.

### Parameters

| Name | Type | Required | Description |
| ---- | ---- | -------- | ----------- |
| template | string | Yes | The path to the HTML template file |
| data | object | Yes | The data to be used in the template |

### Request Body

```json
{
  "template": "invoice.html",
  "data": {
    "customer_name": "John Doe",
    "invoice_number": "INV-001",
    "items": [
      {
        "name": "Product A",
        "quantity": 2,
        "price": 10.99
      },
      {
        "name": "Product B",
        "quantity": 1,
        "price": 19.99
      }
    ]
  }
}
```

### Response

```json
{
  "pdf_url": "https://example.com/invoice.pdf"
}
```

### Error Codes

| Status Code | Description |
| ----------- | ----------- |
| 400 | Bad Request - Missing or invalid parameters |
| 404 | Not Found - Template file not found |
| 500 | Internal Server Error - Error generating PDF |

## `GET /pdf/{id}`

Retrieve a previously generated PDF document.

### Parameters

| Name | Type | Required | Description |
| ---- | ---- | -------- | ----------- |
| id | string | Yes | The ID of the PDF document to retrieve |

### Response

```json
{
  "pdf_url": "https://example.com/invoice.pdf"
}
```

### Error Codes

| Status Code | Description |
| ----------- | ----------- |
| 404 | Not Found - PDF document not found |

## `POST /pdf/batch`

Generate multiple PDF documents from a batch of HTML templates and data.

### Parameters

| Name | Type | Required | Description |
| ---- | ---- | -------- | ----------- |
| batch | array | Yes | An array of objects containing the template and data for each PDF |

### Request Body

```json
{
  "batch": [
    {
      "template": "invoice.html",
      "data": {
        "customer_name": "John Doe",
        "invoice_number": "INV-001",
        "items": [
          {
            "name": "Product A",
            "quantity": 2,
            "price": 10.99
          },
          {
            "name": "Product B",
            "quantity": 1,
            "price": 19.99
          }
        ]
      }
    },
    {
      "template": "receipt.html",
      "data": {
        "customer_name": "Jane Smith",
        "transaction_id": "TX-002",
        "items": [
          {
            "name": "Service A",
            "quantity": 1,
            "price": 50.00
          }
        ]
      }
    }
  ]
}
```

### Response

```json
{
  "pdf_urls": [
    "https://example.com/invoice.pdf",
    "https://example.com/receipt.pdf"
  ]
}
```

### Error Codes

| Status Code | Description |
| ----------- | ----------- |
| 400 | Bad Request - Missing or invalid parameters |
| 404 | Not Found - Template file not found |
| 500 | Internal Server Error - Error generating PDFs |

## `DELETE /pdf/{id}`

Delete a previously generated PDF document.

### Parameters

| Name | Type | Required | Description |
| ---- | ---- | -------- | ----------- |
| id | string | Yes | The ID of the PDF document to delete |

### Response

```json
{
  "message": "PDF document deleted"
}
```

### Error Codes

| Status Code | Description |
| ----------- | ----------- |
| 404 | Not Found - PDF document not found |
| 500 | Internal Server Error - Error deleting PDF |