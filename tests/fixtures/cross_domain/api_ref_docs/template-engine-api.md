---
title: Template Engine API
description: A RESTful API for generating dynamic HTML templates.
keywords: [template, engine, HTML, rendering, dynamic]
category: api-reference
---

## GET /templates
Retrieve a list of available templates.

### Parameters
| Name | Type | Description |
| --- | --- | --- |
| `page` | integer | The page number to retrieve (default: 1) |
| `limit` | integer | The number of results to return per page (default: 10) |

### Response
```json
{
  "templates": [
    {
      "id": "1",
      "name": "Default Layout",
      "description": "A basic HTML layout with header and footer."
    },
    {
      "id": "2",
      "name": "Blog Post",
      "description": "A template for rendering blog post content."
    },
    {
      "id": "3",
      "name": "Product Page",
      "description": "A template for displaying product information."
    }
  ],
  "total": 3,
  "page": 1,
  "limit": 10
}
```

### Error Codes
| Status Code | Description |
| --- | --- |
| 400 | Bad Request - Invalid parameters |
| 500 | Internal Server Error - Failed to retrieve templates |

## GET /templates/{id}
Retrieve a specific template by its ID.

### Parameters
| Name | Type | Description |
| --- | --- | --- |
| `id` | string | The ID of the template to retrieve |

### Response
```json
{
  "id": "1",
  "name": "Default Layout",
  "description": "A basic HTML layout with header and footer.",
  "content": "<!DOCTYPE html>\n<html>\n  <head>\n    <title>{{ title }}</title>\n  </head>\n  <body>\n    <header>\n      <nav>\n        <ul>\n          <li><a href=\"/\">Home</a></li>\n          <li><a href=\"/about\">About</a></li>\n          <li><a href=\"/contact\">Contact</a></li>\n        </ul>\n      </nav>\n    </header>\n    <main>\n      {{ content }}\n    </main>\n    <footer>\n      &copy; {{ year }} My Website\n    </footer>\n  </body>\n</html>"
}
```

### Error Codes
| Status Code | Description |
| --- | --- |
| 404 | Not Found - Template not found |
| 500 | Internal Server Error - Failed to retrieve template |

## POST /templates
Create a new template.

### Request Body
```json
{
  "name": "Product Page",
  "description": "A template for displaying product information.",
  "content": "<!DOCTYPE html>\n<html>\n  <head>\n    <title>{{ product.name }}</title>\n  </head>\n  <body>\n    <header>\n      <nav>\n        <ul>\n          <li><a href=\"/\">Home</a></li>\n          <li><a href=\"/products\">Products</a></li>\n        </ul>\n      </nav>\n    </header>\n    <main>\n      <h1>{{ product.name }}</h1>\n      <p>{{ product.description }}</p>\n      <p>Price: {{ product.price }}</p>\n    </main>\n    <footer>\n      &copy; {{ year }} My Website\n    </footer>\n  </body>\n</html>"
}
```

### Response
```json
{
  "id": "3",
  "name": "Product Page",
  "description": "A template for displaying product information.",
  "content": "<!DOCTYPE html>\n<html>\n  <head>\n    <title>{{ product.name }}</title>\n  </head>\n  <body>\n    <header>\n      <nav>\n        <ul>\n          <li><a href=\"/\">Home</a></li>\n          <li><a href=\"/products\">Products</a></li>\n        </ul>\n      </nav>\n    </header>\n    <main>\n      <h1>{{ product.name }}</h1>\n      <p>{{ product.description }}</p>\n      <p>Price: {{ product.price }}</p>\n    </main>\n    <footer>\n      &copy; {{ year }} My Website\n    </footer>\n  </body>\n</html>"
}
```

### Error Codes
| Status Code | Description |
| --- | --- |
| 400 | Bad Request - Invalid request body |
| 500 | Internal Server Error - Failed to create template |

## PUT /templates/{id}
Update an existing template.

### Parameters
| Name | Type | Description |
| --- | --- | --- |
| `id` | string | The ID of the template to update |

### Request Body
```json
{
  "name": "Updated Product Page",
  "description": "A template for displaying product information with additional details.",
  "content": "<!DOCTYPE html>\n<html>\n  <head>\n    <title>{{ product.name }}</title>\n  </head>\n  <body>\n    <header>\n      <nav>\n        <ul>\n          <li><a href=\"/\">Home</a></li>\n          <li><a href=\"/products\">Products</a></li>\n        </ul>\n      </nav>\n    </header>\n    <main>\n      <h1>{{ product.name }}</h1>\n      <p>{{ product.description }}</p>\n      <p>Price: {{ product.price }}</p>\n      <p>SKU: {{ product.sku }}</p>\n      <p>In Stock: {{ product.inStock }}</p>\n    </main>\n    <footer>\n      &copy; {{ year }} My Website\n    </footer>\n  </body>\n</html>"
}
```

### Response
```json
{
  "id": "3",
  "name": "Updated Product Page",
  "description": "A template for displaying product information with additional details.",
  "content": "<!DOCTYPE html>\n<html>\n  <head>\n    <title>{{ product.name }}</title>\n  </head>\n  <body>\n    <header>\n      <nav>\n        <ul>\n          <li><a href=\"/\">Home</a></li>\n          <li><a href=\"/products\">Products</a></li>\n        </ul>\n      </nav>\n    </header>\n    <main>\n      <h1>{{ product.name }}</h1>\n      <p>{{ product.description }}</p>\n      <p>Price: {{ product.price }}</p>\n      <p>SKU: {{ product.sku }}</p>\n      <p>In Stock: {{ product.inStock }}</p>\n    </main>\n    <footer>\n      &copy; {{ year }} My Website\n    </footer>\n  </body>\n</html>"
}
```

### Error Codes
| Status Code | Description |
| --- | --- |
| 404 | Not Found - Template not found |
| 400 | Bad Request - Invalid request body |
| 500 | Internal Server Error - Failed to update template |