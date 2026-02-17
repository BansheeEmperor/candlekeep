---
title: Cache Management API
description: Manage the caching of content and data on the server.
keywords: [cache, caching, invalidation, purge, clear]
category: api-reference
---

## GET /cache/status
Retrieve the current status of the cache.

### Parameters
None

### Response
```json
{
  "status": "active",
  "size": 1024,
  "hits": 10000,
  "misses": 1000
}
```

## POST /cache/purge
Purge the entire cache.

### Parameters
None

### Request Body
None

### Response
```json
{
  "status": "success",
  "message": "Cache has been purged."
}
```

## POST /cache/purge/{key}
Purge a specific cache entry by key.

### Parameters
| Name | Type | Description |
| --- | --- | --- |
| key | string | The cache key to purge. |

### Request Body
None

### Response
```json
{
  "status": "success",
  "message": "Cache entry for key '{key}' has been purged."
}
```

## POST /cache/invalidate
Invalidate the entire cache.

### Parameters
None

### Request Body
None

### Response
```json
{
  "status": "success",
  "message": "Cache has been invalidated."
}
```

## POST /cache/invalidate/{key}
Invalidate a specific cache entry by key.

### Parameters
| Name | Type | Description |
| --- | --- | --- |
| key | string | The cache key to invalidate. |

### Request Body
None

### Response
```json
{
  "status": "success",
  "message": "Cache entry for key '{key}' has been invalidated."
}
```

### Error Codes
| Status Code | Description |
| --- | --- |
| 400 Bad Request | The request was malformed or missing required parameters. |
| 404 Not Found | The specified cache key was not found. |
| 500 Internal Server Error | An unexpected error occurred while processing the request. |

The Cache Management API provides a set of endpoints for managing the caching of content and data on the server. This API allows you to:

- Retrieve the current status of the cache
- Purge the entire cache or a specific cache entry
- Invalidate the entire cache or a specific cache entry

The API uses standard HTTP methods and JSON for request and response payloads.