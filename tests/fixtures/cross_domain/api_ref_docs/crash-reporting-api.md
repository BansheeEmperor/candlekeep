---
title: Crash Reporting API
description: An API for reporting and managing crashes in a software application.
keywords: [crash reporting, error tracking, bug management, application monitoring]
category: api-reference
---

## POST /crashes
Report a new crash in the application.

### Parameters
| Name | Type | Required | Description |
| ---- | ---- | -------- | ----------- |
| `userId` | string | Yes | The unique identifier of the user who experienced the crash. |
| `deviceInfo` | object | Yes | Information about the device, including OS, version, model, etc. |
| `stackTrace` | string | Yes | The full stack trace of the crash. |
| `timestamp` | string | Yes | The timestamp of when the crash occurred, in ISO 8601 format. |
| `metadata` | object | No | Additional metadata about the crash, such as app version, screen information, etc. |

### Request Body
```json
{
  "userId": "abc123",
  "deviceInfo": {
    "os": "iOS",
    "version": "14.5.1",
    "model": "iPhone 12 Pro"
  },
  "stackTrace": "TypeError: Cannot read property 'length' of undefined\n    at myFunction (/app/index.js:24:16)\n    at anotherFunction (/app/utils.js:42:8)\n    ...",
  "timestamp": "2023-04-15T12:34:56Z",
  "metadata": {
    "appVersion": "2.3.1",
    "screenSize": "1125x2436"
  }
}
```

### Response
```json
{
  "id": "crash-123456",
  "status": "received"
}
```

### Error Codes
| Code | Description |
| ---- | ----------- |
| 400 | Missing required parameters or invalid data format. |
| 429 | Too many requests in a given time period. |

## GET /crashes
Retrieve a list of all crashes reported for the application.

### Parameters
| Name | Type | Required | Description |
| ---- | ---- | -------- | ----------- |
| `limit` | integer | No | The maximum number of crashes to return per page. Default is 25, max is 100. |
| `offset` | integer | No | The number of crashes to skip, for pagination. Default is 0. |
| `status` | string | No | Filter crashes by status, e.g. "received", "under-review", "resolved". |
| `userId` | string | No | Filter crashes by the user who reported them. |

### Response
```json
{
  "total": 142,
  "crashes": [
    {
      "id": "crash-123456",
      "userId": "abc123",
      "deviceInfo": {
        "os": "iOS",
        "version": "14.5.1",
        "model": "iPhone 12 Pro"
      },
      "stackTrace": "TypeError: Cannot read property 'length' of undefined\n    at myFunction (/app/index.js:24:16)\n    at anotherFunction (/app/utils.js:42:8)\n    ...",
      "timestamp": "2023-04-15T12:34:56Z",
      "metadata": {
        "appVersion": "2.3.1",
        "screenSize": "1125x2436"
      },
      "status": "received"
    },
    {
      "id": "crash-123457",
      "userId": "def456",
      "deviceInfo": {
        "os": "Android",
        "version": "11.0",
        "model": "Samsung Galaxy S21"
      },
      "stackTrace": "NullPointerException: Attempt to invoke virtual method 'java.lang.String java.lang.Object.toString()' on a null object reference\n    at com.example.app.MainActivity.onCreate(MainActivity.java:42)\n    at android.app.Activity.performCreate(Activity.java:7136)\n    ...",
      "timestamp": "2023-04-14T09:22:17Z",
      "metadata": {
        "appVersion": "3.1.0",
        "screenSize": "1080x2400"
      },
      "status": "under-review"
    }
  ]
}
```

### Error Codes
| Code | Description |
| ---- | ----------- |
| 400 | Invalid query parameters. |

## GET /crashes/{id}
Retrieve details of a specific crash.

### Parameters
| Name | Type | Required | Description |
| ---- | ---- | -------- | ----------- |
| `id` | string | Yes | The unique identifier of the crash. |

### Response
```json
{
  "id": "crash-123456",
  "userId": "abc123",
  "deviceInfo": {
    "os": "iOS",
    "version": "14.5.1",
    "model": "iPhone 12 Pro"
  },
  "stackTrace": "TypeError: Cannot read property 'length' of undefined\n    at myFunction (/app/index.js:24:16)\n    at anotherFunction (/app/utils.js:42:8)\n    ...",
  "timestamp": "2023-04-15T12:34:56Z",
  "metadata": {
    "appVersion": "2.3.1",
    "screenSize": "1125x2436"
  },
  "status": "received"
}
```

### Error Codes
| Code | Description |
| ---- | ----------- |
| 404 | Crash with the specified ID not found. |

## PATCH /crashes/{id}
Update the status of a specific crash.

### Parameters
| Name | Type | Required | Description |
| ---- | ---- | -------- | ----------- |
| `id` | string | Yes | The unique identifier of the crash. |

### Request Body
```json
{
  "status": "under-review"
}
```

### Response
```json
{
  "id": "crash-123456",
  "status": "under-review"
}
```

### Error Codes
| Code | Description |
| ---- | ----------- |
| 404 | Crash with the specified ID not found. |
| 400 | Invalid status value. |