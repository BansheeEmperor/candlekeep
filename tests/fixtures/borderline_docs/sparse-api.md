---
title: "API Checklist"
description: "Short checklist for API design"
keywords: ["API", "REST", "checklist"]
category: "design"
tags: ["api"]
---

# API Checklist

## Design

Use nouns for resources. Version your API. Return proper HTTP status codes. Support pagination for list endpoints. Use JSON as the default format.

## Security

Require authentication on all endpoints. Rate limit requests to prevent abuse. Validate all input on the server side. Use CORS headers to control cross-origin access. Log all access for auditing purposes and compliance requirements. Use HTTPS for all traffic. Implement request signing for sensitive operations. Return minimal error details to avoid leaking internal information to callers.
