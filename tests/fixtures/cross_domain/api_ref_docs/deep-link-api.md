---
title: Deep Link API
description: An API to create and manage deep links for your mobile application.
keywords: [deep links, mobile, app, marketing, analytics]
category: api-reference
---

## Create Deep Link

### Description
Create a new deep link for your mobile application.

### HTTP Method
`POST`

### Path
`/deep-links`

### Parameters
| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `target_url` | `string` | Yes | The destination URL for the deep link. |
| `campaign` | `string` | No | The campaign associated with the deep link. |
| `source` | `string` | No | The source of the deep link (e.g., email, social media). |
| `medium` | `string` | No | The marketing medium for the deep link (e.g., banner, push notification). |

### Request Body
```json
{
  "target_url": "https://example.com/product/123",
  "campaign": "summer-sale",
  "source": "email",
  "medium": "banner"
}
```

### Response
```json
{
  "id": "abc123",
  "deep_link": "https://example.com/app?link=abc123",
  "target_url": "https://example.com/product/123",
  "campaign": "summer-sale",
  "source": "email",
  "medium": "banner",
  "created_at": "2023-04-01T12:00:00Z"
}
```

### Error Codes
| Status Code | Description |
| --- | --- |
| `400 Bad Request` | The request body is invalid or missing required parameters. |
| `401 Unauthorized` | The API key is invalid or missing. |
| `500 Internal Server Error` | An unexpected error occurred on the server. |

## Retrieve Deep Link

### Description
Retrieve an existing deep link by its ID.

### HTTP Method
`GET`

### Path
`/deep-links/{id}`

### Parameters
| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | Yes | The ID of the deep link to retrieve. |

### Response
```json
{
  "id": "abc123",
  "deep_link": "https://example.com/app?link=abc123",
  "target_url": "https://example.com/product/123",
  "campaign": "summer-sale",
  "source": "email",
  "medium": "banner",
  "created_at": "2023-04-01T12:00:00Z"
}
```

### Error Codes
| Status Code | Description |
| --- | --- |
| `404 Not Found` | The requested deep link was not found. |
| `401 Unauthorized` | The API key is invalid or missing. |
| `500 Internal Server Error` | An unexpected error occurred on the server. |

## Update Deep Link

### Description
Update an existing deep link.

### HTTP Method
`PATCH`

### Path
`/deep-links/{id}`

### Parameters
| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | Yes | The ID of the deep link to update. |

### Request Body
```json
{
  "target_url": "https://example.com/product/456",
  "campaign": "fall-sale",
  "source": "social",
  "medium": "post"
}
```

### Response
```json
{
  "id": "abc123",
  "deep_link": "https://example.com/app?link=abc123",
  "target_url": "https://example.com/product/456",
  "campaign": "fall-sale",
  "source": "social",
  "medium": "post",
  "created_at": "2023-04-01T12:00:00Z",
  "updated_at": "2023-04-15T09:30:00Z"
}
```

### Error Codes
| Status Code | Description |
| --- | --- |
| `404 Not Found` | The requested deep link was not found. |
| `400 Bad Request` | The request body is invalid or missing required parameters. |
| `401 Unauthorized` | The API key is invalid or missing. |
| `500 Internal Server Error` | An unexpected error occurred on the server. |

## Delete Deep Link

### Description
Delete an existing deep link.

### HTTP Method
`DELETE`

### Path
`/deep-links/{id}`

### Parameters
| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | Yes | The ID of the deep link to delete. |

### Response
```json
{
  "message": "Deep link deleted successfully."
}
```

### Error Codes
| Status Code | Description |
| --- | --- |
| `404 Not Found` | The requested deep link was not found. |
| `401 Unauthorized` | The API key is invalid or missing. |
| `500 Internal Server Error` | An unexpected error occurred on the server. |