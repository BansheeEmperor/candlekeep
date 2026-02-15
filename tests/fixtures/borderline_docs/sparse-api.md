---
title: "API Checklist"
description: "Short checklist for API design"
keywords: ["API", "REST", "checklist"]
category: "design"
tags: ["api"]
---

# API Checklist

## Design

Use nouns for resources. Version your API. Return proper HTTP status codes. Support pagination for list endpoints. Use JSON as the default format. APIs should be consistent. All endpoints should follow the same patterns. Naming conventions matter. Keep URLs short and readable. Use plural nouns for collections.

## Request Handling

Validate all input parameters. Return clear error messages. Support filtering and sorting on list endpoints. Use query parameters for optional filters. Use path parameters for resource identifiers. Accept JSON request bodies. Set reasonable request size limits. Handle malformed requests gracefully.

## Response Format

Return consistent response structures. Include metadata in list responses. Use envelope patterns for error responses. Return appropriate content types. Support content negotiation when needed. Include pagination links in list responses. Return timestamps in ISO 8601 format. Use camelCase for JSON field names.

## Security

Require authentication on all endpoints. Rate limit requests to prevent abuse. Validate all input on the server side. Use CORS headers to control cross-origin access. Log all access for auditing purposes and compliance requirements. Use HTTPS for all traffic. Implement request signing for sensitive operations. Return minimal error details to avoid leaking internal information to callers.

## Documentation

Document all endpoints. Include request and response examples. List all possible error codes. Describe authentication requirements. Keep documentation up to date. Use OpenAPI or similar specification formats. Provide a getting started guide. Include rate limit information.
