---
title: Device Registration API
description: API for registering new devices with the platform
keywords: [device, registration, platform, IoT, embedded]
category: api-reference
---

## POST /devices

Register a new device with the platform.

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `deviceId` | string | Yes | Unique identifier for the device |
| `deviceType` | string | Yes | Type of device (e.g. "thermostat", "camera") |
| `location` | object | Yes | Location details for the device |
| `location.latitude` | number | Yes | Latitude coordinate |
| `location.longitude` | number | Yes | Longitude coordinate |
| `location.altitude` | number | No | Altitude (optional) |
| `metadata` | object | No | Additional metadata about the device |

### Request Body

```json
{
  "deviceId": "thermostat-001",
  "deviceType": "thermostat",
  "location": {
    "latitude": 37.7749,
    "longitude": -122.4194,
    "altitude": 10
  },
  "metadata": {
    "model": "Acme T100",
    "serialNumber": "ABC123"
  }
}
```

### Response

```json
{
  "deviceId": "thermostat-001",
  "registrationDate": "2023-04-01T12:00:00Z"
}
```

### Error Codes

| Status Code | Description |
| --- | --- |
| 400 Bad Request | Invalid request body or parameters |
| 409 Conflict | Device ID already registered |
| 500 Internal Server Error | Unexpected server error |

## GET /devices/{deviceId}

Retrieve details for a registered device.

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `deviceId` | string | Yes | Unique identifier for the device |

### Response

```json
{
  "deviceId": "thermostat-001",
  "deviceType": "thermostat",
  "location": {
    "latitude": 37.7749,
    "longitude": -122.4194,
    "altitude": 10
  },
  "metadata": {
    "model": "Acme T100",
    "serialNumber": "ABC123"
  },
  "registrationDate": "2023-04-01T12:00:00Z"
}
```

### Error Codes

| Status Code | Description |
| --- | --- |
| 404 Not Found | Device not found |
| 500 Internal Server Error | Unexpected server error |

## PUT /devices/{deviceId}

Update the details of a registered device.

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `deviceId` | string | Yes | Unique identifier for the device |

### Request Body

```json
{
  "deviceType": "thermostat",
  "location": {
    "latitude": 37.7750,
    "longitude": -122.4195,
    "altitude": 15
  },
  "metadata": {
    "model": "Acme T200",
    "serialNumber": "DEF456"
  }
}
```

### Response

```json
{
  "deviceId": "thermostat-001",
  "deviceType": "thermostat",
  "location": {
    "latitude": 37.7750,
    "longitude": -122.4195,
    "altitude": 15
  },
  "metadata": {
    "model": "Acme T200",
    "serialNumber": "DEF456"
  },
  "registrationDate": "2023-04-01T12:00:00Z"
}
```

### Error Codes

| Status Code | Description |
| --- | --- |
| 404 Not Found | Device not found |
| 400 Bad Request | Invalid request body or parameters |
| 500 Internal Server Error | Unexpected server error |

## DELETE /devices/{deviceId}

Unregister a device from the platform.

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `deviceId` | string | Yes | Unique identifier for the device |

### Response

```json
{
  "message": "Device unregistered successfully"
}
```

### Error Codes

| Status Code | Description |
| --- | --- |
| 404 Not Found | Device not found |
| 500 Internal Server Error | Unexpected server error |