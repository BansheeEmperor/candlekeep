---
title: "How to Implement JWT Authentication"
description: "A step-by-step guide to implementing JWT authentication in a web application using Node.js and Express."
keywords: ["jwt", "authentication", "tokens", "node.js", "express"]
category: "jwt"
tags: ["jwt", "authentication", "node.js", "express"]
---

## Introduction

JSON Web Tokens (JWT) are a widely used standard for securely transmitting information between a client and a server as a JSON object. JWTs are commonly used for authentication and authorization in web applications, as they provide a compact and self-contained way to verify the identity of a user.

In this guide, you will learn how to implement JWT authentication in a web application built with Node.js and Express. We'll cover the process of generating JWT tokens, setting claims, sending tokens in the Authorization header, validating tokens on the server, and handling token expiry.

## Generating JWT Tokens

To generate a JWT token, you'll need to use a JWT library, such as the popular `jsonwebtoken` package. First, install the library:

```
npm install jsonwebtoken
```

Then, in your Express application, create a route or middleware function that generates a new JWT token. Here's an example:

```javascript
const jwt = require('jsonwebtoken');

// Generate a new JWT token
app.post('/login', (req, res) => {
  // Verify the user's credentials
  const { username, password } = req.body;
  if (username === 'admin' && password === 'password') {
    // Create the JWT payload
    const payload = {
      sub: 'user-123',
      iat: Math.floor(Date.now() / 1000),
      exp: Math.floor(Date.now() / 1000) + (60 * 60) // Token expires in 1 hour
    };

    // Sign the token with a secret key
    const token = jwt.sign(payload, 'your_secret_key', { algorithm: 'HS256' });

    res.json({ token });
  } else {
    res.status(401).json({ error: 'Invalid credentials' });
  }
});
```

In this example, we're creating a JWT token with the following claims:

- `sub`: The subject of the token, which is a unique identifier for the user.
- `iat`: The time at which the token was issued, in seconds since the Unix epoch.
- `exp`: The time at which the token will expire, in seconds since the Unix epoch.

We then sign the token using a secret key and the `HS256` algorithm. The secret key should be a long, random string that is kept secure on the server.

## Sending the Token in the Authorization Header

Once the client has received the JWT token, they should include it in the `Authorization` header of subsequent requests to the server. The header should use the `Bearer` scheme, like this:

```
Authorization: Bearer <token>
```

Here's an example of how a client might send the token in a request using the Fetch API:

```javascript
fetch('/protected-resource', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
})
.then(response => response.json())
.then(data => console.log(data))
.catch(error => console.error(error));
```

## Validating JWT Tokens on the Server

When the server receives a request with a JWT token in the `Authorization` header, it needs to validate the token to ensure that it is valid and has not been tampered with. You can use the `jsonwebtoken` library to do this:

```javascript
const jwt = require('jsonwebtoken');

app.get('/protected-resource', (req, res) => {
  // Get the token from the Authorization header
  const token = req.headers.authorization.split(' ')[1];

  try {
    // Verify the token
    const decoded = jwt.verify(token, 'your_secret_key');

    // The token is valid, so you can now use the decoded payload
    console.log(decoded.sub); // 'user-123'
    console.log(decoded.iat); // 1618317600
    console.log(decoded.exp); // 1618321200

    res.json({ message: 'Access granted' });
  } catch (err) {
    // The token is invalid
    res.status(401).json({ error: 'Invalid token' });
  }
});
```

In this example, we're extracting the token from the `Authorization` header, and then using the `jwt.verify()` function to validate the token. If the token is valid, we can access the claims in the payload, such as the subject (`sub`) and the expiration time (`exp`). If the token is invalid, we return a 401 Unauthorized response.

## Handling Token Expiry

JWT tokens have an expiration time, which is set in the `exp` claim. When a token expires, the client will need to obtain a new token. You can handle this in your application by checking the `exp` claim when validating the token. If the token has expired, you can return a 401 Unauthorized response and instruct the client to obtain a new token.

Alternatively, you can implement a "refresh token" system, where the client can exchange an expired access token for a new one. This involves generating a separate refresh token that has a longer expiration time, and using that to obtain a new access token when the current one expires.

## Conclusion

In this guide, you've learned how to implement JWT authentication in a web application using Node.js and Express. You've seen how to generate JWT tokens, set claims, send tokens in the Authorization header, validate tokens on the server, and handle token expiry. With this knowledge, you can now integrate JWT authentication into your own web applications to securely authenticate and authorize users.