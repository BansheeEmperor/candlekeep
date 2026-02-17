---
title: Compliance Scan API
description: Perform compliance scans on cloud resources and infrastructure
keywords: [compliance, security, audit, cloud, infrastructure]
category: api-reference
---

## GET /scans
Retrieve a list of all completed compliance scans.

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| `page` | integer | The page number to retrieve (default: 1) | No |
| `limit` | integer | The number of results to return per page (default: 20) | No |
| `status` | string | Filter scans by status (e.g., "completed", "failed") | No |

### Response
```json
{
  "total_count": 100,
  "page": 1,
  "limit": 20,
  "scans": [
    {
      "id": "abc123",
      "status": "completed",
      "started_at": "2023-04-01T12:00:00Z",
      "completed_at": "2023-04-01T12:15:00Z",
      "resource_count": 50,
      "failed_count": 2
    },
    {
      "id": "def456",
      "status": "failed",
      "started_at": "2023-04-02T09:30:00Z",
      "completed_at": "2023-04-02T09:45:00Z",
      "resource_count": 30,
      "failed_count": 10
    }
  ]
}
```

## POST /scans
Create a new compliance scan.

### Request Body
```json
{
  "name": "Monthly Compliance Audit",
  "description": "Scan all cloud resources for compliance",
  "scope": {
    "resource_types": ["aws_instance", "aws_s3_bucket", "azure_vm"],
    "regions": ["us-east-1", "us-west-2", "eu-west-1"]
  },
  "schedule": {
    "type": "recurring",
    "interval": "monthly",
    "start_date": "2023-05-01"
  },
  "rules": [
    {
      "name": "Ensure S3 buckets have encryption enabled",
      "resource_type": "aws_s3_bucket",
      "check": "encryption_enabled"
    },
    {
      "name": "Ensure EC2 instances have MFA enabled",
      "resource_type": "aws_instance",
      "check": "mfa_enabled"
    }
  ]
}
```

### Response
```json
{
  "id": "ghi789",
  "name": "Monthly Compliance Audit",
  "description": "Scan all cloud resources for compliance",
  "status": "queued",
  "started_at": null,
  "completed_at": null,
  "resource_count": 0,
  "failed_count": 0
}
```

## GET /scans/{id}
Retrieve details of a specific compliance scan.

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| `id` | string | The ID of the scan to retrieve | Yes |

### Response
```json
{
  "id": "abc123",
  "name": "Monthly Compliance Audit",
  "description": "Scan all cloud resources for compliance",
  "status": "completed",
  "started_at": "2023-04-01T12:00:00Z",
  "completed_at": "2023-04-01T12:15:00Z",
  "resource_count": 50,
  "failed_count": 2,
  "results": [
    {
      "resource_id": "i-0123456789abcdef",
      "resource_type": "aws_instance",
      "check": "mfa_enabled",
      "status": "failed",
      "details": "Instance does not have MFA enabled"
    },
    {
      "resource_id": "my-s3-bucket",
      "resource_type": "aws_s3_bucket",
      "check": "encryption_enabled",
      "status": "passed",
      "details": "Bucket has server-side encryption enabled"
    }
  ]
}
```

## DELETE /scans/{id}
Cancel a pending compliance scan.

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| `id` | string | The ID of the scan to cancel | Yes |

### Response
```json
{
  "id": "abc123",
  "status": "canceled"
}
```

## Error Codes
| Status Code | Description |
| --- | --- |
| 400 Bad Request | Invalid request parameters or body |
| 404 Not Found | The requested resource was not found |
| 500 Internal Server Error | An unexpected error occurred on the server |