---
title: File Storage API
description: Manage file uploads and downloads for your application
keywords: [file storage, file upload, file download, api, rest]
category: api-reference
---

## Upload File
### POST /files

Upload a new file to the server.

### Parameters
| Name | Type | Required | Description |
| --- | --- | --- | --- |
| file | file | Yes | The file to be uploaded |
| metadata | object | No | Additional metadata about the file |

### Request Body
```json
{
  "file": "<binary file data>",
  "metadata": {
    "filename": "example.jpg",
    "description": "A sample image file",
    "tags": ["image", "sample"]
  }
}
```

### Response
```json
{
  "id": "f12345678",
  "filename": "example.jpg",
  "size": 1024,
  "url": "https://example.com/files/f12345678",
  "metadata": {
    "description": "A sample image file",
    "tags": ["image", "sample"]
  }
}
```

### Error Codes
- `400 Bad Request`: Missing required parameters or invalid file data
- `413 Payload Too Large`: File size exceeds the maximum allowed limit
- `500 Internal Server Error`: Unexpected server error

## Download File
### GET /files/{id}

Download a file by its ID.

### Parameters
| Name | Type | Required | Description |
| --- | --- | --- | --- |
| id | string | Yes | The unique identifier of the file to download |

### Response
The raw file data.

### Error Codes
- `404 Not Found`: File with the specified ID does not exist
- `500 Internal Server Error`: Unexpected server error

## List Files
### GET /files

Retrieve a list of files.

### Parameters
| Name | Type | Required | Description |
| --- | --- | --- | --- |
| page | integer | No | The page number to retrieve (default: 1) |
| limit | integer | No | The number of results to return per page (default: 20) |
| search | string | No | Search query to filter the results |
| sort | string | No | The field to sort the results by (e.g., `created_at`, `size`) |
| order | string | No | The sort order (asc or desc) |

### Response
```json
{
  "data": [
    {
      "id": "f12345678",
      "filename": "example.jpg",
      "size": 1024,
      "url": "https://example.com/files/f12345678",
      "metadata": {
        "description": "A sample image file",
        "tags": ["image", "sample"]
      }
    },
    {
      "id": "f87654321",
      "filename": "document.pdf",
      "size": 2048,
      "url": "https://example.com/files/f87654321",
      "metadata": {
        "description": "A sample PDF document",
        "tags": ["document", "pdf"]
      }
    }
  ],
  "meta": {
    "total": 50,
    "page": 1,
    "limit": 20
  }
}
```

### Error Codes
- `500 Internal Server Error`: Unexpected server error

## Delete File
### DELETE /files/{id}

Delete a file by its ID.

### Parameters
| Name | Type | Required | Description |
| --- | --- | --- | --- |
| id | string | Yes | The unique identifier of the file to delete |

### Response
```json
{
  "message": "File deleted successfully"
}
```

### Error Codes
- `404 Not Found`: File with the specified ID does not exist
- `500 Internal Server Error`: Unexpected server error