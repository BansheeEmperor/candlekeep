---
title: Batch Processing API
description: Asynchronous batch processing of large data sets
keywords: [batch processing, asynchronous, data processing, job management]
category: api-reference
---

## `POST /jobs`
Create a new batch processing job.

### Parameters
| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `name` | `string` | Yes | Friendly name for the job |
| `description` | `string` | No | Optional description of the job |
| `input_source` | `string` | Yes | Source location of the input data (e.g. S3 bucket) |
| `output_destination` | `string` | Yes | Destination location for the processed output (e.g. S3 bucket) |
| `processor` | `string` | Yes | Name of the data processing algorithm to apply |
| `priority` | `integer` | No | Optional priority level (0-100) for the job |

### Request Body
```json
{
  "name": "Customer Data Processing",
  "description": "Process customer records and generate reports",
  "input_source": "s3://my-bucket/customer-data",
  "output_destination": "s3://my-bucket/processed-data",
  "processor": "customer-data-processor",
  "priority": 50
}
```

### Response
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "name": "Customer Data Processing",
  "status": "queued",
  "created_at": "2023-04-01T12:00:00Z",
  "updated_at": "2023-04-01T12:00:00Z"
}
```

### Error Codes
- `400 Bad Request`: Invalid request parameters
- `403 Forbidden`: Insufficient permissions to create a job
- `500 Internal Server Error`: Unexpected error occurred while creating the job

## `GET /jobs`
List all batch processing jobs.

### Parameters
| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `status` | `string` | No | Filter jobs by status (e.g. `queued`, `running`, `completed`, `failed`) |
| `limit` | `integer` | No | Maximum number of jobs to return (default: 20) |
| `offset` | `integer` | No | Offset for pagination (default: 0) |

### Response
```json
[
  {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "name": "Customer Data Processing",
    "status": "queued",
    "created_at": "2023-04-01T12:00:00Z",
    "updated_at": "2023-04-01T12:00:00Z"
  },
  {
    "id": "456e4567-e89b-12d3-a456-426614174000",
    "name": "Product Inventory Update",
    "status": "running",
    "created_at": "2023-03-31T15:30:00Z",
    "updated_at": "2023-04-01T10:45:00Z"
  }
]
```

### Error Codes
- `400 Bad Request`: Invalid request parameters
- `403 Forbidden`: Insufficient permissions to list jobs
- `500 Internal Server Error`: Unexpected error occurred while fetching jobs

## `GET /jobs/{id}`
Retrieve details of a specific batch processing job.

### Parameters
| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | Yes | Unique identifier of the job |

### Response
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "name": "Customer Data Processing",
  "description": "Process customer records and generate reports",
  "status": "completed",
  "input_source": "s3://my-bucket/customer-data",
  "output_destination": "s3://my-bucket/processed-data",
  "processor": "customer-data-processor",
  "priority": 50,
  "created_at": "2023-04-01T12:00:00Z",
  "updated_at": "2023-04-01T12:30:00Z",
  "started_at": "2023-04-01T12:05:00Z",
  "completed_at": "2023-04-01T12:25:00Z"
}
```

### Error Codes
- `404 Not Found`: Job with the specified ID not found
- `403 Forbidden`: Insufficient permissions to view the job
- `500 Internal Server Error`: Unexpected error occurred while fetching the job

## `DELETE /jobs/{id}`
Cancel a batch processing job.

### Parameters
| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | Yes | Unique identifier of the job |

### Response
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "name": "Customer Data Processing",
  "status": "cancelled",
  "created_at": "2023-04-01T12:00:00Z",
  "updated_at": "2023-04-01T12:15:00Z"
}
```

### Error Codes
- `404 Not Found`: Job with the specified ID not found
- `403 Forbidden`: Insufficient permissions to cancel the job
- `409 Conflict`: Job is in a state that cannot be cancelled (e.g. already completed)
- `500 Internal Server Error`: Unexpected error occurred while cancelling the job