---
title: Runbook Automation API
description: Programmatically manage runbooks and automate IT operations tasks.
keywords: [runbook, automation, IT operations, task management, API]
category: api-reference
---

## GET /runbooks
Retrieve a list of available runbooks.

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| page | integer | Page number for pagination | No |
| per_page | integer | Number of results per page | No |
| search | string | Search query to filter runbooks | No |

### Response
```json
{
  "data": [
    {
      "id": "123456",
      "name": "Server Provisioning",
      "description": "Automates the process of provisioning a new server",
      "tags": ["server", "provisioning", "automation"]
    },
    {
      "id": "789012",
      "name": "Backup Database",
      "description": "Backs up the production database to a secure location",
      "tags": ["database", "backup", "security"]
    }
  ],
  "meta": {
    "total_count": 25,
    "current_page": 1,
    "total_pages": 5
  }
}
```

## POST /runbooks
Create a new runbook.

### Request Body
```json
{
  "name": "Restart Web Server",
  "description": "Restarts the production web server",
  "steps": [
    {
      "name": "Stop Web Server",
      "command": "/etc/init.d/apache2 stop"
    },
    {
      "name": "Start Web Server",
      "command": "/etc/init.d/apache2 start"
    }
  ],
  "tags": ["web", "server", "restart"]
}
```

### Response
```json
{
  "id": "345678",
  "name": "Restart Web Server",
  "description": "Restarts the production web server",
  "steps": [
    {
      "name": "Stop Web Server",
      "command": "/etc/init.d/apache2 stop"
    },
    {
      "name": "Start Web Server",
      "command": "/etc/init.d/apache2 start"
    }
  ],
  "tags": ["web", "server", "restart"]
}
```

## GET /runbooks/{id}
Retrieve details of a specific runbook.

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| id | string | Unique identifier of the runbook | Yes |

### Response
```json
{
  "id": "123456",
  "name": "Server Provisioning",
  "description": "Automates the process of provisioning a new server",
  "steps": [
    {
      "name": "Create Virtual Machine",
      "command": "terraform apply -var-file=production.tfvars"
    },
    {
      "name": "Install Operating System",
      "command": "ansible-playbook os-install.yml"
    },
    {
      "name": "Configure Services",
      "command": "ansible-playbook services-config.yml"
    }
  ],
  "tags": ["server", "provisioning", "automation"]
}
```

## POST /runbooks/{id}/execute
Execute a runbook.

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| id | string | Unique identifier of the runbook | Yes |

### Request Body
```json
{
  "parameters": {
    "vm_name": "web-server-01",
    "os_version": "ubuntu-20.04"
  }
}
```

### Response
```json
{
  "id": "987654",
  "runbook_id": "123456",
  "status": "running",
  "start_time": "2023-04-13T10:15:00Z",
  "end_time": null,
  "output": ""
}
```

## GET /runbook-executions
Retrieve a list of recent runbook executions.

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| page | integer | Page number for pagination | No |
| per_page | integer | Number of results per page | No |
| runbook_id | string | Filter by runbook ID | No |
| status | string | Filter by execution status (running, completed, failed) | No |

### Response
```json
{
  "data": [
    {
      "id": "987654",
      "runbook_id": "123456",
      "status": "completed",
      "start_time": "2023-04-13T10:15:00Z",
      "end_time": "2023-04-13T10:20:00Z",
      "output": "Server provisioned successfully."
    },
    {
      "id": "654321",
      "runbook_id": "789012",
      "status": "failed",
      "start_time": "2023-04-12T15:30:00Z",
      "end_time": "2023-04-12T15:35:00Z",
      "output": "Error: Unable to connect to database."
    }
  ],
  "meta": {
    "total_count": 10,
    "current_page": 1,
    "total_pages": 2
  }
}
```

## Error Codes
| Status Code | Description |
| --- | --- |
| 400 Bad Request | Invalid request parameters or payload |
| 401 Unauthorized | Invalid or missing authentication credentials |
| 404 Not Found | Requested resource not found |
| 500 Internal Server Error | Unexpected server error |