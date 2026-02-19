---
title: "JWT Token Structure and Validation Reference"
description: "A technical reference for JWT structure, encoding, and validation"
keywords: ["jwt", "token", "claims", "signature", "validation", "authentication"]
category: "jwt"
tags: ["jwt", "authentication", "security", "web"]
---

## JWT Token Structure

A JSON Web Token (JWT) is a compact, URL-safe means of representing claims to be transferred between two parties. The token is composed of three parts:

1. **Header**: Contains metadata about the token, including the signing algorithm used (e.g. `HS256`, `RS256`) and the token type (`JWT`).
2. **Payload**: Contains the claims, which are statements about the entity (typically the user) and additional metadata. Common registered claims include `sub` (subject), `exp` (expiration time), `iat` (issued at), `iss` (issuer), and `aud` (audience).
3. **Signature**: A digital signature created by hashing the header and payload with a secret key.

The three parts are Base64URL encoded and concatenated with periods (`.`) to form the final JWT string.

### Header
The header contains two required fields:

- `alg`: The signing algorithm used, such as `HS256` (HMAC SHA-256) or `RS256` (RSA SHA-256).
- `typ`: The token type, which is always `JWT`.

Example header:
```json
{
  "alg": "HS256",
  "typ": "JWT"
}
```

### Payload
The payload contains the claims, which are statements about the entity (typically the user) and additional metadata. Common registered claims include:

- `sub` (subject): The principal that is the subject of the JWT.
- `exp` (expiration time): The time at which the JWT expires, represented in seconds since the Unix Epoch.
- `iat` (issued at): The time at which the JWT was issued, represented in seconds since the Unix Epoch.
- `iss` (issuer): The principal that issued the JWT.
- `aud` (audience): The intended recipient of the JWT.

You can also include custom claims, which are application-specific data.

Example payload:
```json
{
  "sub": "1234567890",
  "name": "John Doe",
  "admin": true,
  "iat": 1516239022,
  "exp": 1516242622
}
```

### Signature
The signature is created by taking the encoded header, the encoded payload, and a secret key, then using the algorithm specified in the header (e.g., HMAC SHA-256) to create a digital signature.

For example, if using the HMAC SHA-256 algorithm, the signature is calculated as follows:

```
HMACSHA256(
  base64UrlEncode(header) + "." +
  base64UrlEncode(payload),
  secret
)
```

The final JWT token is the concatenation of the three parts, separated by periods:

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiYWRtaW4iOnRydWUsImlhdCI6MTUxNjIzOTAyMiwiZXhwIjoxNTE2MjQyNjIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c
```

## JWT Validation

To validate a JWT token, you need to perform the following steps:

1. **Decode the token**: Split the token into its three parts (header, payload, signature) by splitting on the `.` characters.
2. **Verify the signature**: Use the signing algorithm specified in the header (e.g., HMAC SHA-256) and the secret key to verify the signature matches the encoded header and payload.
3. **Validate the claims**: Check that the claims in the payload are valid, such as ensuring the token hasn't expired (`exp` claim) and the issuer (`iss` claim) is trusted.

Here's an example of decoding a JWT token using the `jsonwebtoken` library in Node.js:

```javascript
const jwt = require('jsonwebtoken');

const token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiYWRtaW4iOnRydWUsImlhdCI6MTUxNjIzOTAyMiwiZXhwIjoxNTE2MjQyNjIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c';

// Decode the token (without verifying the signature)
const decoded = jwt.decode(token, { complete: true });
console.log(decoded.header); // { "alg": "HS256", "typ": "JWT" }
console.log(decoded.payload); // { "sub": "1234567890", "name": "John Doe", "admin": true, "iat": 1516239022, "exp": 1516242622 }
```

To verify the signature and validate the claims, you'll need to use the secret key used to sign the token:

```javascript
const secret = 'your_secret_key';

try {
  // Verify the token
  const verified = jwt.verify(token, secret);
  console.log(verified);
} catch (err) {
  console.error('Invalid token:', err);
}
```

The `jwt.verify()` function will throw an error if the token is invalid (e.g., the signature doesn't match, the token has expired, etc.).

## Conclusion

JWTs provide a compact and secure way to transmit information between parties as a JSON object. By understanding the structure of a JWT, including the header, payload, and signature, you can effectively validate and work with JWT tokens in your applications.