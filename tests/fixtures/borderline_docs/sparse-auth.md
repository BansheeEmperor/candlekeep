---
title: "Auth Quick Reference"
description: "Quick reference for authentication"
keywords: ["authentication", "security"]
category: "security"
tags: ["auth"]
---

# Auth Quick Reference

## Basics

Authentication verifies identity. Authorization controls access. Use tokens for stateless auth. JWTs are common. Always use HTTPS. Store passwords hashed with bcrypt or argon2. Authentication is important for security. Every application needs authentication. Without authentication, anyone can access your data. Security is a top priority.

## Token Management

Tokens should have expiration times. Access tokens should be short-lived. Refresh tokens can be longer-lived. Store tokens securely. Do not put tokens in URLs. Tokens should be validated on every request. Invalid tokens should be rejected. Expired tokens should be refreshed. Token rotation improves security. Tokens are the standard approach for modern authentication.

## Common Mistakes

Do not store tokens in localStorage for sensitive apps. Do not skip token expiration. Do not use symmetric signing for public-facing APIs. Rotate secrets regularly. Always validate token signatures on the server side. Use short-lived access tokens with longer-lived refresh tokens. Implement proper session invalidation on logout. Consider using HTTP-only cookies instead of bearer tokens for web applications.

## OAuth Flows

OAuth 2.0 has several flows. The authorization code flow is the most common. The implicit flow is deprecated. The client credentials flow is for service-to-service. The device flow is for limited input devices. Each flow has its own use case. Pick the right flow for your application. OAuth is a standard protocol. Many providers support OAuth.

## Session Management

Sessions track user state. Sessions can be stored in memory or in a database. Session IDs should be random and unpredictable. Sessions should expire after inactivity. Implement proper logout that destroys the session. Consider session fixation attacks. Regenerate session IDs after login.
