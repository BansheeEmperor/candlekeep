---
title: Image Processing API
description: A RESTful API for processing and manipulating images.
keywords: [image, processing, upload, resize, filter, convert]
category: api-reference
---

## `POST /images/upload`
Upload a new image.

### Parameters
| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `file` | `file` | Yes | The image file to upload. Supported formats: JPEG, PNG, GIF. |

### Request Body
```json
{
  "file": "binary_image_data"
}
```

### Response
```json
{
  "id": "123456789",
  "filename": "example.jpg",
  "size": 123456,
  "width": 1920,
  "height": 1080,
  "format": "jpeg"
}
```

### Error Codes
| Status Code | Description |
| --- | --- |
| 400 | Invalid file format or missing required parameters. |
| 413 | File size exceeds the maximum allowed limit. |
| 500 | Internal server error. |

## `GET /images/{id}`
Retrieve information about a specific image.

### Parameters
| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | Yes | The unique identifier of the image. |

### Response
```json
{
  "id": "123456789",
  "filename": "example.jpg",
  "size": 123456,
  "width": 1920,
  "height": 1080,
  "format": "jpeg",
  "uploaded_at": "2023-04-01T12:00:00Z"
}
```

### Error Codes
| Status Code | Description |
| --- | --- |
| 404 | Image not found. |
| 500 | Internal server error. |

## `POST /images/{id}/resize`
Resize an image.

### Parameters
| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | Yes | The unique identifier of the image. |
| `width` | `integer` | Yes | The desired width of the resized image. |
| `height` | `integer` | Yes | The desired height of the resized image. |
| `maintain_aspect_ratio` | `boolean` | No | Whether to maintain the aspect ratio of the image. Default is `true`. |

### Request Body
```json
{
  "width": 800,
  "height": 600,
  "maintain_aspect_ratio": true
}
```

### Response
```json
{
  "id": "123456789",
  "filename": "example_resized.jpg",
  "size": 67890,
  "width": 800,
  "height": 600,
  "format": "jpeg"
}
```

### Error Codes
| Status Code | Description |
| --- | --- |
| 404 | Image not found. |
| 400 | Invalid parameters or unable to resize the image. |
| 500 | Internal server error. |

## `POST /images/{id}/filter`
Apply a filter to an image.

### Parameters
| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | Yes | The unique identifier of the image. |
| `filter` | `string` | Yes | The type of filter to apply. Supported filters: `grayscale`, `sepia`, `blur`, `sharpen`. |

### Request Body
```json
{
  "filter": "grayscale"
}
```

### Response
```json
{
  "id": "123456789",
  "filename": "example_filtered.jpg",
  "size": 89012,
  "width": 1920,
  "height": 1080,
  "format": "jpeg"
}
```

### Error Codes
| Status Code | Description |
| --- | --- |
| 404 | Image not found. |
| 400 | Invalid filter or unable to apply the filter. |
| 500 | Internal server error. |

## `POST /images/{id}/convert`
Convert an image to a different format.

### Parameters
| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | Yes | The unique identifier of the image. |
| `format` | `string` | Yes | The desired output format. Supported formats: `jpeg`, `png`, `gif`. |

### Request Body
```json
{
  "format": "png"
}
```

### Response
```json
{
  "id": "123456789",
  "filename": "example.png",
  "size": 98765,
  "width": 1920,
  "height": 1080,
  "format": "png"
}
```

### Error Codes
| Status Code | Description |
| --- | --- |
| 404 | Image not found. |
| 400 | Invalid format or unable to convert the image. |
| 500 | Internal server error. |