---
title: "Authentication and Authorization"
description: "Security patterns for user authentication and access control"
keywords: ["authentication", "authorization", "security", "OAuth", "JWT"]
category: "security"
tags: ["auth", "security", "oauth", "jwt"]
---

# Authentication and Authorization

## Authentication (Who are you?)

### Session-Based
Server stores session state:
```
1. User logs in
2. Server creates session, stores in DB/cache
3. Returns session ID in cookie
4. Client sends cookie with each request
```
**Pros**: Server controls sessions, easy revocation  
**Cons**: Stateful, doesn't scale horizontally

### Token-Based (JWT)
Stateless authentication:
```
1. User logs in
2. Server generates JWT token
3. Client stores token (localStorage/cookie)
4. Client sends token in Authorization header
```
**Pros**: Stateless, scales horizontally  
**Cons**: Can't revoke before expiry, token size

JWT Structure:
```
Header.Payload.Signature
eyJhbGc...  # Base64 encoded
```

### OAuth 2.0
Delegated authorization:
- **Authorization Code**: Web apps (most secure)
- **Implicit**: SPAs (deprecated)
- **Client Credentials**: Service-to-service
- **Password**: Legacy (not recommended)

### Multi-Factor Authentication (MFA)
Require multiple factors:
- Something you know (password)
- Something you have (phone, token)
- Something you are (biometric)

## Authorization (What can you do?)

### Role-Based Access Control (RBAC)
Users assigned roles with permissions:
```
User -> Role -> Permissions
john -> admin -> [read, write, delete]
jane -> viewer -> [read]
```

### Attribute-Based Access Control (ABAC)
Policies based on attributes:
```
IF user.department == "finance" 
   AND resource.type == "invoice"
   AND time.hour >= 9 AND time.hour <= 17
THEN allow
```

### Access Control Lists (ACL)
Per-resource permissions:
```
document_123:
  - john: read, write
  - jane: read
  - team_finance: read, write
```

## Security Best Practices

### Password Storage
Never store plaintext passwords:
```
hash = bcrypt(password + salt)
```
Use bcrypt, scrypt, or Argon2.

### Token Security
- Short expiration (15 min access, 7 day refresh)
- HTTPS only
- HttpOnly cookies (prevent XSS)
- Secure flag (HTTPS only)
- SameSite flag (prevent CSRF)

### API Security
- Rate limiting
- Input validation
- SQL injection prevention
- XSS protection
- CORS configuration

### Principle of Least Privilege
Grant minimum permissions needed.
