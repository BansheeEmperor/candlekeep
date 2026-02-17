---
title: Document Signing API
description: Securely sign and manage digital documents.
keywords: [document, signing, electronic signature, digital signature, authentication]
category: api-reference
---

## POST /documents

Create a new document for signing.

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| name | string | Yes | The name of the document. |
| file | file | Yes | The document file to be signed. |

### Request Body

```json
{
  "name": "NDA_2023.pdf",
  "file": "<binary_file_data>"
}
```

### Response

```json
{
  "id": "abc123",
  "name": "NDA_2023.pdf",
  "status": "pending",
  "signers": []
}
```

### Error Codes

| Code | Description |
| --- | --- |
| 400 | Invalid request parameters. |
| 415 | Unsupported media type. |
| 500 | Internal server error. |

## POST /documents/{id}/signers

Add a signer to a document.

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| id | string | Yes | The ID of the document. |
| name | string | Yes | The name of the signer. |
| email | string | Yes | The email address of the signer. |

### Request Body

```json
{
  "name": "John Doe",
  "email": "john.doe@example.com"
}
```

### Response

```json
{
  "id": "abc123",
  "name": "NDA_2023.pdf",
  "status": "pending",
  "signers": [
    {
      "name": "John Doe",
      "email": "john.doe@example.com",
      "status": "pending"
    }
  ]
}
```

### Error Codes

| Code | Description |
| --- | --- |
| 400 | Invalid request parameters. |
| 404 | Document not found. |
| 500 | Internal server error. |

## POST /documents/{id}/sign

Sign a document.

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| id | string | Yes | The ID of the document. |
| signer_id | string | Yes | The ID of the signer. |
| signature | string | Yes | The base64-encoded signature image. |

### Request Body

```json
{
  "signer_id": "abc123",
  "signature": "<base64_encoded_signature_image>"
}
```

### Response

```json
{
  "id": "abc123",
  "name": "NDA_2023.pdf",
  "status": "signed",
  "signers": [
    {
      "name": "John Doe",
      "email": "john.doe@example.com",
      "status": "signed"
    }
  ]
}
```

### Error Codes

| Code | Description |
| --- | --- |
| 400 | Invalid request parameters. |
| 404 | Document or signer not found. |
| 409 | Document already signed. |
| 500 | Internal server error. |

## GET /documents/{id}

Retrieve a document's details.

### Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| id | string | Yes | The ID of the document. |

### Response

```json
{
  "id": "abc123",
  "name": "NDA_2023.pdf",
  "status": "signed",
  "signers": [
    {
      "name": "John Doe",
      "email": "john.doe@example.com",
      "status": "signed"
    }
  ]
}
```

### Error Codes

| Code | Description |
| --- | --- |
| 404 | Document not found. |
| 500 | Internal server error. |