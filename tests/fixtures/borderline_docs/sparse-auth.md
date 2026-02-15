---
title: "Auth Quick Reference"
description: "Quick reference for authentication"
keywords: ["authentication", "security"]
category: "security"
tags: ["auth"]
---

# Auth Quick Reference

## Basics

Authentication verifies identity. Authorization controls access. Use tokens for stateless auth. JWTs are common. Always use HTTPS. Store passwords hashed with bcrypt or argon2.

## Common Mistakes

Do not store tokens in localStorage for sensitive apps. Do not skip token expiration. Do not use symmetric signing for public-facing APIs. Rotate secrets regularly. Always validate token signatures on the server side. Use short-lived access tokens with longer-lived refresh tokens. Implement proper session invalidation on logout. Consider using HTTP-only cookies instead of bearer tokens for web applications.
