---
title: App Configuration API
description: Manage your app's configuration settings
keywords: [app, configuration, settings, api, rest]
category: api-reference
---

## GET /config

Retrieve the current configuration settings for your app.

### Parameters

| Name | Type | Description |
| --- | --- | --- |
| `environment` | string | (Optional) The environment to fetch the configuration for. Defaults to `production`. |

### Response

```json
{
  "settings": {
    "apiKey": "abc123",
    "databaseUrl": "postgres://user:pass@host/mydb",
    "emailFrom": "noreply@myapp.com",
    "stripePublishableKey": "pk_test_1234"
  }
}
```

### Error Codes

| Status Code | Description |
| --- | --- |
| 400 | Invalid request parameters |
| 404 | Configuration not found |
| 500 | Internal server error |

## POST /config

Create a new configuration setting.

### Parameters

| Name | Type | Description |
| --- | --- | --- |
| `environment` | string | (Optional) The environment to create the configuration for. Defaults to `production`. |

### Request Body

```json
{
  "key": "newSetting",
  "value": "my-new-value"
}
```

### Response

```json
{
  "key": "newSetting",
  "value": "my-new-value",
  "environment": "production"
}
```

### Error Codes

| Status Code | Description |
| --- | --- |
| 400 | Invalid request body |
| 409 | Configuration setting already exists |
| 500 | Internal server error |

## PUT /config/{key}

Update an existing configuration setting.

### Parameters

| Name | Type | Description |
| --- | --- | --- |
| `key` | string | The key of the configuration setting to update. |
| `environment` | string | (Optional) The environment to update the configuration for. Defaults to `production`. |

### Request Body

```json
{
  "value": "new-value"
}
```

### Response

```json
{
  "key": "myKey",
  "value": "new-value",
  "environment": "production"
}
```

### Error Codes

| Status Code | Description |
| --- | --- |
| 400 | Invalid request body or parameters |
| 404 | Configuration setting not found |
| 500 | Internal server error |

## DELETE /config/{key}

Delete a configuration setting.

### Parameters

| Name | Type | Description |
| --- | --- | --- |
| `key` | string | The key of the configuration setting to delete. |
| `environment` | string | (Optional) The environment to delete the configuration from. Defaults to `production`. |

### Response

```json
{
  "message": "Configuration setting deleted"
}
```

### Error Codes

| Status Code | Description |
| --- | --- |
| 404 | Configuration setting not found |
| 500 | Internal server error |