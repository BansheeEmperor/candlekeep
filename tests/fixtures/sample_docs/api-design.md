---
title: "API Design Best Practices"
description: "Guidelines for designing RESTful APIs"
keywords: ["API", "REST", "HTTP", "design", "endpoints"]
category: "design"
tags: ["api", "rest", "http", "web"]
---

# API Design Best Practices

## REST Principles

RESTful APIs follow these core principles:
- **Stateless**: Each request contains all information needed
- **Resource-based**: URLs represent resources, not actions
- **HTTP methods**: GET (read), POST (create), PUT (update), DELETE (remove)
- **Standard status codes**: 200 OK, 201 Created, 400 Bad Request, 404 Not Found, 500 Server Error

## URL Structure

Use nouns for resources, not verbs:
```
GET    /users          # List users
GET    /users/123      # Get user 123
POST   /users          # Create user
PUT    /users/123      # Update user 123
DELETE /users/123      # Delete user 123
```

## Versioning

Include version in URL or header:
```
/v1/users
/v2/users
```

## Error Handling

Return consistent error format:
```json
{
  "error": {
    "code": "INVALID_INPUT",
    "message": "Email is required",
    "field": "email"
  }
}
```

## Pagination

For large datasets:
```
GET /users?page=2&limit=50
```

Response includes metadata:
```json
{
  "data": [...],
  "pagination": {
    "page": 2,
    "limit": 50,
    "total": 1000
  }
}
```
