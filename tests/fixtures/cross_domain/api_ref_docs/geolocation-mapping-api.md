---
title: Geolocation Mapping API
description: A RESTful API for accessing and managing geographic location data.
keywords: [geolocation, mapping, location, coordinates, geocoding]
category: api-reference
---

## GET /locations

Retrieves a list of geographic locations.

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `latitude` | number | optional | The latitude to filter locations by. |
| `longitude` | number | optional | The longitude to filter locations by. |
| `radius` | number | optional | The search radius in meters. |
| `limit` | integer | optional | The maximum number of results to return. |
| `offset` | integer | optional | The number of results to skip. |

### Response

```json
{
  "data": [
    {
      "id": "1234",
      "name": "Central Park",
      "latitude": 40.7828,
      "longitude": -73.9653,
      "address": "Central Park, New York, NY 10024, USA"
    },
    {
      "id": "5678",
      "name": "Eiffel Tower",
      "latitude": 48.8584,
      "longitude": 2.2945,
      "address": "Champ de Mars, 5 Avenue Anatole France, 75007 Paris, France"
    }
  ],
  "meta": {
    "total_count": 2,
    "limit": 10,
    "offset": 0
  }
}
```

### Error Codes

| Status Code | Description |
| --- | --- |
| 400 | Bad request - Invalid parameters provided. |
| 500 | Internal server error - An unexpected error occurred. |

## GET /locations/{id}

Retrieves a specific geographic location by its ID.

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | string | true | The unique identifier of the location. |

### Response

```json
{
  "data": {
    "id": "1234",
    "name": "Central Park",
    "latitude": 40.7828,
    "longitude": -73.9653,
    "address": "Central Park, New York, NY 10024, USA"
  }
}
```

### Error Codes

| Status Code | Description |
| --- | --- |
| 404 | Not found - The specified location was not found. |
| 500 | Internal server error - An unexpected error occurred. |

## POST /locations

Creates a new geographic location.

### Request Body

```json
{
  "name": "Eiffel Tower",
  "latitude": 48.8584,
  "longitude": 2.2945,
  "address": "Champ de Mars, 5 Avenue Anatole France, 75007 Paris, France"
}
```

### Response

```json
{
  "data": {
    "id": "5678",
    "name": "Eiffel Tower",
    "latitude": 48.8584,
    "longitude": 2.2945,
    "address": "Champ de Mars, 5 Avenue Anatole France, 75007 Paris, France"
  }
}
```

### Error Codes

| Status Code | Description |
| --- | --- |
| 400 | Bad request - Invalid data provided in the request body. |
| 500 | Internal server error - An unexpected error occurred. |

## PUT /locations/{id}

Updates an existing geographic location.

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | string | true | The unique identifier of the location. |

### Request Body

```json
{
  "name": "Eiffel Tower (Updated)",
  "latitude": 48.8584,
  "longitude": 2.2945,
  "address": "Champ de Mars, 5 Avenue Anatole France, 75007 Paris, France"
}
```

### Response

```json
{
  "data": {
    "id": "5678",
    "name": "Eiffel Tower (Updated)",
    "latitude": 48.8584,
    "longitude": 2.2945,
    "address": "Champ de Mars, 5 Avenue Anatole France, 75007 Paris, France"
  }
}
```

### Error Codes

| Status Code | Description |
| --- | --- |
| 400 | Bad request - Invalid data provided in the request body. |
| 404 | Not found - The specified location was not found. |
| 500 | Internal server error - An unexpected error occurred. |