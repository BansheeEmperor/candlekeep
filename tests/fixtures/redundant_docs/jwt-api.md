---
title: "Securing REST APIs with JWT Tokens"
description: "A guide to protecting REST API endpoints with JWT authentication and authorization."
keywords: ["jwt", "authentication", "authorization", "rest api", "middleware", "claims", "refresh token"]
category: "jwt"
tags: ["jwt", "authentication", "authorization", "rest api", "middleware"]
---

## Introduction

Securing your REST API endpoints is crucial to prevent unauthorized access and protect your application's data. JSON Web Tokens (JWT) provide a robust and flexible authentication and authorization mechanism that is widely adopted in modern web applications. In this guide, we'll explore how to use JWT to secure your REST API, covering essential topics such as token validation middleware, role-based access control, protecting specific routes, handling unauthorized requests, and token refresh.

## Setting up JWT Validation Middleware

The first step in securing your REST API with JWT is to set up middleware to validate incoming tokens. This middleware will intercept requests, extract the JWT from the `Authorization` header, and verify its validity before allowing the request to proceed.

Here's an example of how you can set up JWT validation middleware using Express.js and the `jsonwebtoken` library:

```javascript
const jwt = require('jsonwebtoken');

const validateJWT = (req, res, next) => {
  // Extract the token from the Authorization header
  const token = req.headers.authorization.split(' ')[1];

  try {
    // Verify the token using the secret key
    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    req.user = decoded;
    next();
  } catch (err) {
    // Handle invalid or expired tokens
    return res.status(401).json({ error: 'Invalid or expired token' });
  }
};

// Apply the middleware to all routes that require authentication
app.use('/api', validateJWT);
```

In this example, the `validateJWT` middleware extracts the JWT from the `Authorization` header, verifies its signature using the `JWT_SECRET` environment variable, and attaches the decoded claims to the `req.user` object. If the token is invalid or expired, the middleware returns a 401 Unauthorized response.

## Role-based Access Control with JWT Claims

JWT tokens can carry additional information, known as claims, that can be used to implement role-based access control (RBAC) for your API. By including relevant claims in the JWT, you can authorize users to access specific routes or perform certain actions based on their roles or permissions.

Here's an example of how you can use JWT claims for RBAC:

```javascript
// Generate a JWT with role claim
const token = jwt.sign({ userId: user.id, role: user.role }, process.env.JWT_SECRET);

// Validate the token and check the role claim
const validateJWT = (req, res, next) => {
  // Extract and verify the token
  const decoded = jwt.verify(token, process.env.JWT_SECRET);

  // Check the user's role and authorize the request accordingly
  if (decoded.role === 'admin') {
    req.user = decoded;
    next();
  } else {
    return res.status(403).json({ error: 'Forbidden' });
  }
};

// Apply the middleware to the admin-only route
app.use('/api/admin', validateJWT);
```

In this example, the JWT is generated with a `role` claim that represents the user's role. The `validateJWT` middleware checks the role claim and allows the request to proceed only if the user has the 'admin' role.

## Protecting Specific Routes

You can selectively protect specific routes in your API by applying the JWT validation middleware to those routes. This allows you to secure sensitive endpoints while leaving public endpoints accessible without authentication.

```javascript
// Protect the /api/users endpoint
app.use('/api/users', validateJWT, (req, res) => {
  // Only authenticated users can access this route
  res.json(users);
});

// Leave the /api/public endpoint unprotected
app.get('/api/public', (req, res) => {
  res.json({ message: 'This is a public endpoint' });
});
```

In this example, the `/api/users` endpoint is protected by the `validateJWT` middleware, while the `/api/public` endpoint remains accessible without authentication.

## Handling Unauthorized Requests (401/403)

When a request is not authorized (401 Unauthorized) or the user is not allowed to perform the requested action (403 Forbidden), you should provide a clear and informative response to the client. This helps them understand the reason for the rejection and take appropriate action.

```javascript
// Handle 401 Unauthorized
app.use((err, req, res, next) => {
  if (err.name === 'UnauthorizedError') {
    return res.status(401).json({ error: 'Unauthorized' });
  }
  next(err);
});

// Handle 403 Forbidden
app.use((err, req, res, next) => {
  if (err.name === 'ForbiddenError') {
    return res.status(403).json({ error: 'Forbidden' });
  }
  next(err);
});
```

In this example, the middleware checks the error name and returns the appropriate HTTP status code and error message.

## Token Refresh Endpoints

To provide a better user experience and improve security, you can implement token refresh endpoints that allow clients to obtain new access tokens without requiring the user to re-authenticate. This is especially useful for long-lived sessions, where the access token may expire before the user is finished using the application.

```javascript
// Generate a refresh token along with the access token
const { accessToken, refreshToken } = generateTokens(user);

// Implement the token refresh endpoint
app.post('/api/refresh', (req, res) => {
  const refreshToken = req.body.refreshToken;

  try {
    const decoded = jwt.verify(refreshToken, process.env.REFRESH_TOKEN_SECRET);
    const newAccessToken = jwt.sign({ userId: decoded.userId }, process.env.JWT_SECRET, { expiresIn: '15m' });
    res.json({ accessToken: newAccessToken });
  } catch (err) {
    return res.status(403).json({ error: 'Invalid refresh token' });
  }
});
```

In this example, the server generates both an access token and a refresh token when the user authenticates. The client can then use the refresh token to obtain a new access token when the current one expires, without requiring the user to re-authenticate.

## API Key vs. JWT

While API keys can be a simple and effective way to authenticate clients, JWT offers several advantages:

- **Stateless**: JWT tokens are self-contained and do not require server-side storage, making the authentication process more scalable.
- **Payload Data**: JWT tokens can carry additional claims and metadata, enabling more sophisticated authorization and access control.
- **Expiry and Revocation**: JWT tokens have an expiry date, and revoked tokens can be easily invalidated across the entire application.
- **Cryptographic Security**: JWT tokens are digitally signed, providing a higher level of security compared to simple API keys.

In general, JWT is a more robust and versatile authentication and authorization solution, especially for complex and long-lived web applications. However, API keys can still be a suitable choice for simple APIs with limited requirements.

## Conclusion

Securing your REST API with JWT is a powerful and flexible way to protect your application's data and resources. By implementing JWT validation middleware, role-based access control, and token refresh endpoints, you can ensure that only authorized users can access and interact with your API. Remember to handle unauthorized requests appropriately and consider the trade-offs between API keys and JWT when choosing the right authentication solution for your application.