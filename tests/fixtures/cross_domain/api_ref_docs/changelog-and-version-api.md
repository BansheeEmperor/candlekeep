---
title: Changelog and Version API
description: API for managing application version information and changelogs
keywords: [changelog, version, release, application, api]
category: api-reference
---

## GET /api/v1/versions

Retrieve a list of all application versions.

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `limit` | integer | No | Maximum number of results to return per page (default: 20, max: 100) |
| `offset` | integer | No | Number of results to skip (default: 0) |
| `order` | string | No | Field to order results by (default: `created_at`) |
| `direction` | string | No | Sort direction (default: `desc`) |

### Response

```json
{
  "data": [
    {
      "id": "1",
      "version": "1.2.3",
      "release_date": "2022-01-01",
      "changelog": "- New feature\n- Bug fixes",
      "created_at": "2022-01-01T12:00:00Z",
      "updated_at": "2022-01-01T12:00:00Z"
    },
    {
      "id": "2",
      "version": "1.2.2",
      "release_date": "2021-12-15",
      "changelog": "- Improvements\n- Minor bug fixes",
      "created_at": "2021-12-15T10:30:00Z",
      "updated_at": "2021-12-15T10:30:00Z"
    }
  ],
  "meta": {
    "total": 2,
    "limit": 20,
    "offset": 0
  }
}
```

### Error Codes

| Status Code | Description |
| --- | --- |
| 400 | Bad request |
| 500 | Internal server error |

## GET /api/v1/versions/{id}

Retrieve a specific application version by ID.

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | string | Yes | ID of the version to retrieve |

### Response

```json
{
  "data": {
    "id": "1",
    "version": "1.2.3",
    "release_date": "2022-01-01",
    "changelog": "- New feature\n- Bug fixes",
    "created_at": "2022-01-01T12:00:00Z",
    "updated_at": "2022-01-01T12:00:00Z"
  }
}
```

### Error Codes

| Status Code | Description |
| --- | --- |
| 404 | Version not found |
| 500 | Internal server error |

## POST /api/v1/versions

Create a new application version.

### Request Body

```json
{
  "version": "1.2.4",
  "release_date": "2022-02-15",
  "changelog": "- New feature\n- Bug fixes"
}
```

### Response

```json
{
  "data": {
    "id": "3",
    "version": "1.2.4",
    "release_date": "2022-02-15",
    "changelog": "- New feature\n- Bug fixes",
    "created_at": "2022-02-15T09:00:00Z",
    "updated_at": "2022-02-15T09:00:00Z"
  }
}
```

### Error Codes

| Status Code | Description |
| --- | --- |
| 400 | Bad request |
| 500 | Internal server error |

## PATCH /api/v1/versions/{id}

Update an existing application version.

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | string | Yes | ID of the version to update |

### Request Body

```json
{
  "version": "1.2.5",
  "release_date": "2022-03-01",
  "changelog": "- Improvements\n- Minor bug fixes"
}
```

### Response

```json
{
  "data": {
    "id": "3",
    "version": "1.2.5",
    "release_date": "2022-03-01",
    "changelog": "- Improvements\n- Minor bug fixes",
    "created_at": "2022-02-15T09:00:00Z",
    "updated_at": "2022-03-01T08:30:00Z"
  }
}
```

### Error Codes

| Status Code | Description |
| --- | --- |
| 404 | Version not found |
| 400 | Bad request |
| 500 | Internal server error |

## DELETE /api/v1/versions/{id}

Delete an existing application version.

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | string | Yes | ID of the version to delete |

### Response

```json
{
  "data": {
    "id": "3",
    "version": "1.2.5",
    "release_date": "2022-03-01",
    "changelog": "- Improvements\n- Minor bug fixes",
    "created_at": "2022-02-15T09:00:00Z",
    "updated_at": "2022-03-01T08:30:00Z"
  }
}
```

### Error Codes

| Status Code | Description |
| --- | --- |
| 404 | Version not found |
| 500 | Internal server error |