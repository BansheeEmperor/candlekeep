---
title: Certificate Management API
description: API for managing digital certificates
keywords: [certificates, PKI, SSL, TLS, X.509]
category: api-reference
---

## GET /certificates

Retrieve a list of all certificates managed by the system.

### Parameters

| Name | Type | Description | Required |
| --- | --- | --- | --- |
| limit | integer | Maximum number of results to return | No |
| offset | integer | Number of results to skip | No |
| status | string | Filter by certificate status (e.g. "active", "revoked") | No |

### Response

```json
{
  "total": 25,
  "results": [
    {
      "id": "c123456",
      "subject": "CN=example.com,O=Example Inc,C=US",
      "issuer": "CN=Example CA,O=Example Inc,C=US",
      "serial_number": "12345678",
      "not_before": "2022-01-01T00:00:00Z",
      "not_after": "2023-01-01T00:00:00Z",
      "status": "active"
    },
    {
      "id": "c987654",
      "subject": "CN=test.example.com,O=Example Inc,C=US",
      "issuer": "CN=Example CA,O=Example Inc,C=US",
      "serial_number": "87654321",
      "not_before": "2021-06-15T00:00:00Z",
      "not_after": "2022-06-15T00:00:00Z",
      "status": "revoked"
    }
  ]
}
```

### Error Codes

| Status Code | Description |
| --- | --- |
| 400 | Invalid request parameters |
| 500 | Internal server error |

## GET /certificates/{id}

Retrieve details for a specific certificate.

### Parameters

| Name | Type | Description | Required |
| --- | --- | --- | --- |
| id | string | ID of the certificate to retrieve | Yes |

### Response

```json
{
  "id": "c123456",
  "subject": "CN=example.com,O=Example Inc,C=US",
  "issuer": "CN=Example CA,O=Example Inc,C=US",
  "serial_number": "12345678",
  "not_before": "2022-01-01T00:00:00Z",
  "not_after": "2023-01-01T00:00:00Z",
  "status": "active",
  "pem_certificate": "-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----"
}
```

### Error Codes

| Status Code | Description |
| --- | --- |
| 404 | Certificate not found |
| 500 | Internal server error |

## POST /certificates

Create a new certificate.

### Request Body

```json
{
  "subject": "CN=example.com,O=Example Inc,C=US",
  "issuer": "CN=Example CA,O=Example Inc,C=US",
  "not_before": "2022-01-01T00:00:00Z",
  "not_after": "2023-01-01T00:00:00Z",
  "key_algorithm": "rsa",
  "key_size": 2048
}
```

### Response

```json
{
  "id": "c123456",
  "subject": "CN=example.com,O=Example Inc,C=US",
  "issuer": "CN=Example CA,O=Example Inc,C=US",
  "serial_number": "12345678",
  "not_before": "2022-01-01T00:00:00Z",
  "not_after": "2023-01-01T00:00:00Z",
  "status": "active",
  "pem_certificate": "-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----"
}
```

### Error Codes

| Status Code | Description |
| --- | --- |
| 400 | Invalid request body |
| 409 | Certificate already exists |
| 500 | Internal server error |

## PATCH /certificates/{id}

Update an existing certificate.

### Parameters

| Name | Type | Description | Required |
| --- | --- | --- | --- |
| id | string | ID of the certificate to update | Yes |

### Request Body

```json
{
  "not_after": "2024-01-01T00:00:00Z"
}
```

### Response

```json
{
  "id": "c123456",
  "subject": "CN=example.com,O=Example Inc,C=US",
  "issuer": "CN=Example CA,O=Example Inc,C=US",
  "serial_number": "12345678",
  "not_before": "2022-01-01T00:00:00Z",
  "not_after": "2024-01-01T00:00:00Z",
  "status": "active",
  "pem_certificate": "-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----"
}
```

### Error Codes

| Status Code | Description |
| --- | --- |
| 404 | Certificate not found |
| 400 | Invalid request body |
| 500 | Internal server error |

## DELETE /certificates/{id}

Revoke an existing certificate.

### Parameters

| Name | Type | Description | Required |
| --- | --- | --- | --- |
| id | string | ID of the certificate to revoke | Yes |

### Response

```json
{
  "id": "c123456",
  "subject": "CN=example.com,O=Example Inc,C=US",
  "issuer": "CN=Example CA,O=Example Inc,C=US",
  "serial_number": "12345678",
  "not_before": "2022-01-01T00:00:00Z",
  "not_after": "2023-01-01T00:00:00Z",
  "status": "revoked"
}
```

### Error Codes

| Status Code | Description |
| --- | --- |
| 404 | Certificate not found |
| 500 | Internal server error |