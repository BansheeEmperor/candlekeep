---
title: VPN Tunnel API
description: Manage VPN tunnel configurations and connections
keywords: [vpn, tunnel, network, security, api]
category: api-reference
---

## GET /vpn/tunnels
Retrieve a list of all configured VPN tunnels.

### Parameters
| Name | Type | Description |
| --- | --- | --- |
| `limit` | integer | Maximum number of results to return (default: 20, max: 100) |
| `offset` | integer | Number of results to skip (default: 0) |

### Response
```json
{
  "total": 42,
  "results": [
    {
      "id": "t-abc123",
      "name": "Main Office VPN",
      "status": "active",
      "endpoint": "vpn.example.com",
      "local_network": "10.0.0.0/24",
      "remote_network": "192.168.1.0/24"
    },
    {
      "id": "t-def456",
      "name": "Backup VPN",
      "status": "inactive",
      "endpoint": "vpn-backup.example.com",
      "local_network": "10.0.1.0/24",
      "remote_network": "192.168.2.0/24"
    }
  ]
}
```

## GET /vpn/tunnels/{id}
Retrieve details for a specific VPN tunnel.

### Parameters
| Name | Type | Description |
| --- | --- | --- |
| `id` | string | ID of the VPN tunnel |

### Response
```json
{
  "id": "t-abc123",
  "name": "Main Office VPN",
  "status": "active",
  "endpoint": "vpn.example.com",
  "local_network": "10.0.0.0/24",
  "remote_network": "192.168.1.0/24",
  "preshared_key": "s3cr3tk3y",
  "ike_version": "v2",
  "encryption": "aes-256-gcm",
  "authentication": "sha256"
}
```

## POST /vpn/tunnels
Create a new VPN tunnel.

### Request Body
```json
{
  "name": "Branch Office VPN",
  "endpoint": "vpn-branch.example.com",
  "local_network": "10.0.2.0/24",
  "remote_network": "192.168.3.0/24",
  "preshared_key": "n3wp@ssw0rd",
  "ike_version": "v1",
  "encryption": "aes-128-cbc",
  "authentication": "sha1"
}
```

### Response
```json
{
  "id": "t-ghi789",
  "name": "Branch Office VPN",
  "status": "pending",
  "endpoint": "vpn-branch.example.com",
  "local_network": "10.0.2.0/24",
  "remote_network": "192.168.3.0/24"
}
```

## PATCH /vpn/tunnels/{id}
Update an existing VPN tunnel.

### Parameters
| Name | Type | Description |
| --- | --- | --- |
| `id` | string | ID of the VPN tunnel |

### Request Body
```json
{
  "name": "Main Office VPN (updated)",
  "encryption": "aes-256-gcm"
}
```

### Response
```json
{
  "id": "t-abc123",
  "name": "Main Office VPN (updated)",
  "status": "active",
  "endpoint": "vpn.example.com",
  "local_network": "10.0.0.0/24",
  "remote_network": "192.168.1.0/24",
  "preshared_key": "s3cr3tk3y",
  "ike_version": "v2",
  "encryption": "aes-256-gcm",
  "authentication": "sha256"
}
```

## DELETE /vpn/tunnels/{id}
Delete a VPN tunnel.

### Parameters
| Name | Type | Description |
| --- | --- | --- |
| `id` | string | ID of the VPN tunnel |

### Response
```json
{
  "id": "t-abc123",
  "name": "Main Office VPN (updated)",
  "status": "deleted"
}
```

### Error Codes
| Code | Description |
| --- | --- |
| 400 | Bad Request - Invalid input data |
| 404 | Not Found - VPN tunnel not found |
| 409 | Conflict - VPN tunnel is in use and cannot be deleted |
| 500 | Internal Server Error - An unexpected error occurred |