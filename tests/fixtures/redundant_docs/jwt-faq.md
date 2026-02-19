---
title: "Common Questions About JWT Authentication"
description: "Answers to frequently asked questions about using JWT for authentication and authorization."
keywords: ["JWT", "authentication", "authorization", "refresh token", "access token", "token expiry", "token revocation", "token storage", "custom claims", "token size"]
category: "jwt"
tags: ["jwt", "authentication", "authorization", "refresh token", "access token"]
---

## Where should I store JWT tokens?

When working with JWT tokens, it's important to store them securely. The recommended approach is to store the access token in memory (e.g. in a variable) and use it for making authenticated requests. The refresh token should be stored in an HttpOnly cookie, which can only be accessed by the server. This helps prevent XSS attacks, where a malicious script could access the token directly from the client-side.

## How do I handle token refresh?

To handle token refresh, you'll typically use a two-token system with an access token and a refresh token. The access token is short-lived (e.g. 15 minutes) and is used for making authenticated requests. The refresh token is long-lived (e.g. 14 days) and is used to obtain a new access token when the current one expires.

When the client's access token expires, the client should send the refresh token to the server. The server can then validate the refresh token and, if valid, issue a new access token (and potentially a new refresh token) to the client.

## What happens when a token expires mid-request?

If a JWT token expires while a request is in progress, the server should respond with an appropriate HTTP status code (e.g. 401 Unauthorized) to indicate that the token is no longer valid. The client should then use the refresh token to obtain a new access token and retry the request.

It's important to handle token expiration gracefully in your application's error handling logic. You can, for example, display a user-friendly message to the client and prompt them to re-authenticate.

## How do I revoke a JWT?

Revoking a JWT is not as straightforward as revoking a traditional session token. Since JWTs are self-contained and can be verified without a central authority, there is no built-in mechanism for revoking them.

One approach is to maintain a blacklist or revocation list on the server side. Whenever a token is revoked, its unique identifier (e.g. the `jti` claim) is added to the blacklist. Before verifying a token, the server checks if the token's identifier is present in the blacklist.

Alternatively, you can set the token's `exp` (expiry) claim to a very short duration (e.g. a few seconds) to effectively revoke the token.

## Should I use JWT for sessions?

While JWT can be used for session management, it's generally not recommended for this purpose. JWTs are designed to be self-contained and stateless, which means they don't require a server-side session store. However, this also means that if a JWT is compromised, it can be used to impersonate the user until it expires.

For session management, it's generally better to use a traditional session-based approach, where the server maintains a session store and issues a session ID to the client. This allows the server to revoke sessions and invalidate tokens if necessary.

## What's the difference between access and refresh tokens?

Access tokens and refresh tokens serve different purposes in a JWT-based authentication system:

- **Access Token**: The access token is a short-lived JWT that is used to make authenticated requests to the server. It typically contains the user's basic information and permissions.
- **Refresh Token**: The refresh token is a long-lived JWT that is used to obtain a new access token when the current one expires. Refresh tokens are typically stored securely on the server-side and are not exposed to the client.

The main difference is that access tokens are designed to be used frequently, while refresh tokens are used less often to obtain new access tokens.

## How do I add custom claims to a JWT?

You can add custom claims to a JWT by including them in the token's payload. For example:

```json
{
  "sub": "1234567890",
  "name": "John Doe",
  "admin": true,
  "iat": 1516239022
}
```

In this example, the `admin` claim is a custom claim that can be used to authorize the user's actions on the server side.

When verifying the token, the server can check the custom claims to make authorization decisions.

## What's the maximum token size?

The maximum size of a JWT token is determined by the maximum size of an HTTP header, which is typically around 8KB. However, it's generally recommended to keep the token size as small as possible, as larger tokens can increase the overhead of every request.

To keep the token size small, you should:

1. Limit the number of claims in the token payload.
2. Use short claim names (e.g. `sub` instead of `subject`).
3. Avoid including large or complex data in the token payload.

If you need to store large amounts of data, consider storing it on the server and including only a reference to that data in the token payload.