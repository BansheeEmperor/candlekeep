# Authentication Guide

## Overview

Candlekeep uses ChromaDB's token-based authentication for secure access control. Authentication is verified at startup and enforced per-operation.

## Configuration

### Environment Variables

```bash
# ChromaDB server URL
CHROMA_URL=http://localhost:8000

# Authentication token (leave empty for no auth)
CHROMA_AUTH_TOKEN=your-secret-token-here
```

### Local Development (No Auth)

For local development without authentication:

```bash
CHROMA_URL=http://localhost:8000
CHROMA_AUTH_TOKEN=
```

Start ChromaDB without auth:
```bash
./scripts/start_chroma.sh
```

### Production (With Auth)

For production with authentication:

```bash
CHROMA_URL=https://your-server.com:8000
CHROMA_AUTH_TOKEN=your-production-token
```

## Access Levels

### Read Access
- **Required for**: All operations
- **Verified at**: MCP server startup
- **Failure behavior**: Server fails to start with error message

Operations requiring read access:
- `search()` - Search knowledge base
- `list_documents()` - List indexed documents
- `get_stats()` - Get database statistics
- `get_categories()` - List categories
- `search_entities()` - Search by entity
- `get_related_documents()` - Find related docs
- `explain_relationship()` - Analyze relationships
- `extract_entities()` - Extract entities

### Write Access
- **Required for**: Modification operations
- **Verified at**: MCP server startup
- **Failure behavior**: Server runs in read-only mode

Operations requiring write access:
- `ingest()` - Add documents
- `delete_document()` - Remove documents
- `repopulate_database()` - Clear and rebuild

## ChromaDB Server Setup

### Without Authentication (Local)

```bash
chroma run --path /data/chroma --host localhost --port 8000
```

### With Authentication (Production)

1. **Generate token:**
```bash
openssl rand -hex 32 > /etc/chroma/tokens.txt
chmod 600 /etc/chroma/tokens.txt
```

2. **Start server:**
```bash
chroma run \
  --path /data/chroma \
  --host 0.0.0.0 \
  --port 8000 \
  --auth-provider token \
  --auth-token-file /etc/chroma/tokens.txt
```

3. **Configure client:**
```bash
# In .env
CHROMA_URL=http://your-server:8000
CHROMA_AUTH_TOKEN=<token-from-file>
```

## Token Management

### Token Format
- ChromaDB uses Bearer token authentication
- Tokens are arbitrary strings (recommend 32+ hex characters)
- Multiple tokens can be configured (one per line in token file)

### Token Rotation

1. **Add new token** to token file:
```bash
echo "new-token-here" >> /etc/chroma/tokens.txt
```

2. **Update clients** with new token

3. **Remove old token** from file after all clients updated

4. **Restart ChromaDB** to apply changes

### Token Storage

**DO:**
- Store tokens in environment variables
- Use secret management systems (HashiCorp Vault)
- Restrict file permissions (chmod 600)

**DON'T:**
- Commit tokens to git
- Share tokens in plain text
- Use weak/predictable tokens

## Security Best Practices

### 1. Use HTTPS in Production
Set up nginx or ALB with SSL termination:
```nginx
server {
    listen 443 ssl;
    server_name chroma.example.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Authorization $http_authorization;
    }
}
```

### 2. Restrict Network Access
- Use security groups to limit IP ranges
- Consider VPN or SSH tunneling
- Don't expose ChromaDB directly to internet

### 3. Separate Read/Write Tokens
- Use different tokens for read-only vs read-write access
- Distribute read-only tokens more widely
- Restrict write tokens to admin users

### 4. Monitor Access
- Check ChromaDB logs for unauthorized attempts
- Set up alerts for authentication failures
- Audit token usage regularly

### 5. Rotate Tokens Regularly
- Rotate production tokens quarterly
- Rotate immediately if token compromised
- Use automated rotation where possible

## Troubleshooting

### "Read access denied"
- Verify CHROMA_AUTH_TOKEN is set correctly
- Check token exists in server's token file
- Ensure no extra whitespace in token

### "Write access denied"
- Token may have read-only permissions
- Check server configuration allows writes
- Verify token in server's token file

### "Connection failed"
- Check CHROMA_URL is correct
- Verify ChromaDB server is running
- Test connectivity: `curl http://your-server:8000/api/v2/heartbeat`

### Server won't start with auth
- Check token file exists and is readable
- Verify file permissions (should be 600)
- Check ChromaDB logs for errors

## Example Configurations

### Development Team
```bash
# .env
CHROMA_URL=http://dev-chroma.internal:8000
CHROMA_AUTH_TOKEN=dev-team-read-write-token
```

### CI/CD Pipeline
```bash
# .env
CHROMA_URL=http://ci-chroma.internal:8000
CHROMA_AUTH_TOKEN=ci-read-only-token
```

### Production
```bash
# .env
CHROMA_URL=https://chroma.prod.example.com:8000
CHROMA_AUTH_TOKEN=${CHROMA_PROD_TOKEN}  # From secrets manager
```
