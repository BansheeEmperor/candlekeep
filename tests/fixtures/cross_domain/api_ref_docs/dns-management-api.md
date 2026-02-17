---
title: DNS Management API
description: Manage DNS records and zones for your domain
keywords: [dns, domain, records, zones, api]
category: api-reference
---

## List Domains
`GET /domains`

### Parameters
| Name | Type | Description |
| --- | --- | --- |
| limit | integer | Maximum number of results to return |
| offset | integer | Number of results to skip |

### Response
```json
{
  "domains": [
    {
      "id": "abc123",
      "name": "example.com",
      "created_at": "2023-04-01T12:00:00Z",
      "updated_at": "2023-04-15T10:30:00Z"
    },
    {
      "id": "def456",
      "name": "mydomain.net",
      "created_at": "2022-11-20T08:45:00Z",
      "updated_at": "2023-03-01T14:20:00Z"
    }
  ],
  "total_count": 2
}
```

### Error Codes
| Code | Description |
| --- | --- |
| 400 | Invalid request parameters |
| 500 | Internal server error |

## Create Domain
`POST /domains`

### Request Body
```json
{
  "name": "newdomain.com"
}
```

### Response
```json
{
  "id": "ghi789",
  "name": "newdomain.com",
  "created_at": "2023-04-20T09:15:00Z",
  "updated_at": "2023-04-20T09:15:00Z"
}
```

### Error Codes
| Code | Description |
| --- | --- |
| 400 | Invalid domain name |
| 409 | Domain already exists |
| 500 | Internal server error |

## Get Domain Details
`GET /domains/{domain_id}`

### Parameters
| Name | Type | Description |
| --- | --- | --- |
| domain_id | string | ID of the domain |

### Response
```json
{
  "id": "abc123",
  "name": "example.com",
  "created_at": "2023-04-01T12:00:00Z",
  "updated_at": "2023-04-15T10:30:00Z"
}
```

### Error Codes
| Code | Description |
| --- | --- |
| 404 | Domain not found |
| 500 | Internal server error |

## List DNS Records
`GET /domains/{domain_id}/records`

### Parameters
| Name | Type | Description |
| --- | --- | --- |
| domain_id | string | ID of the domain |
| type | string | Filter by record type (A, CNAME, MX, etc.) |
| name | string | Filter by record name |

### Response
```json
{
  "records": [
    {
      "id": "rec123",
      "domain_id": "abc123",
      "type": "A",
      "name": "www",
      "value": "192.168.1.100",
      "ttl": 300,
      "created_at": "2023-04-01T12:00:00Z",
      "updated_at": "2023-04-10T15:20:00Z"
    },
    {
      "id": "rec456",
      "domain_id": "abc123",
      "type": "CNAME",
      "name": "blog",
      "value": "example.com",
      "ttl": 600,
      "created_at": "2023-04-05T09:30:00Z",
      "updated_at": "2023-04-12T11:45:00Z"
    }
  ],
  "total_count": 2
}
```

### Error Codes
| Code | Description |
| --- | --- |
| 404 | Domain not found |
| 500 | Internal server error |

## Create DNS Record
`POST /domains/{domain_id}/records`

### Request Body
```json
{
  "type": "A",
  "name": "www",
  "value": "192.168.1.100",
  "ttl": 300
}
```

### Response
```json
{
  "id": "rec789",
  "domain_id": "abc123",
  "type": "A",
  "name": "www",
  "value": "192.168.1.100",
  "ttl": 300,
  "created_at": "2023-04-20T09:45:00Z",
  "updated_at": "2023-04-20T09:45:00Z"
}
```

### Error Codes
| Code | Description |
| --- | --- |
| 404 | Domain not found |
| 400 | Invalid record data |
| 409 | Record already exists |
| 500 | Internal server error |