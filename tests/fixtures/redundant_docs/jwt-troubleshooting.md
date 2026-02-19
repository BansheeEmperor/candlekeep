---
title: "Debugging JWT Authentication Errors"
description: "A troubleshooting guide for common JWT problems: 'jwt malformed' errors, 'TokenExpiredError', 'invalid signature', clock skew issues, wrong algorithm errors, missing Bearer prefix, CORS issues with Authorization header."
keywords: ["jwt", "authentication", "troubleshooting", "debugging", "error", "malformed", "expired", "signature", "clock skew", "algorithm", "bearer", "cors"]
category: "jwt"
tags: ["jwt", "authentication", "error", "troubleshooting"]
---

## Debugging JWT Authentication Errors

When integrating JWT (JSON Web Token) authentication into your application, you may encounter various errors that can be challenging to diagnose and resolve. This guide will walk you through the most common JWT-related errors and provide steps to help you debug and fix them.

### "jwt malformed" Error

The `"jwt malformed"` error typically indicates that the JWT token provided is not in the correct format. This can happen for several reasons:

1. **Incorrect Token Format**: Ensure that the JWT token is in the correct format, which is `header.payload.signature`.
2. **Encoding/Decoding Issues**: Check that the token is properly encoded and decoded. Use a tool like [jwt.io](https://jwt.io/) to inspect the token and identify any issues with the header, payload, or signature.
3. **Tampering**: Verify that the token has not been tampered with, as this will cause the malformed error.

To fix this error, double-check the token format, ensure proper encoding/decoding, and investigate any potential tampering.

### "TokenExpiredError"

The `"TokenExpiredError"` indicates that the JWT token has expired and is no longer valid. This can happen when the token's `exp` (expiry) claim is in the past.

1. **Check Token Expiry**: Inspect the token's `exp` claim to ensure that it has not expired.
2. **Implement Refresh Tokens**: Use refresh tokens to obtain new access tokens when the current one expires. This allows users to remain authenticated without requiring them to log in again.
3. **Adjust Token Expiry**: If the token expiry is too short, consider increasing the `exp` claim value to allow for longer session durations.

To resolve this error, implement a refresh token flow or adjust the token expiry time as needed.

### "invalid signature" Error

The `"invalid signature"` error occurs when the JWT signature verification fails. This can happen for the following reasons:

1. **Incorrect Secret Key**: Ensure that the secret key used to sign the token is the same as the one used to verify the signature.
2. **Wrong Algorithm**: Verify that the signing algorithm (e.g., HS256, RS256) matches the one used to verify the signature.
3. **Key Rotation**: If you're using asymmetric keys (RSA), make sure the verification key is up-to-date, especially if you're rotating keys.

To fix this error, double-check the secret key, signing algorithm, and key rotation (if applicable).

### Clock Skew Issues

Clock skew issues can cause JWT verification to fail, even if the token is valid. This can happen when the server and client clocks are not synchronized.

1. **Adjust Clock Skew Tolerance**: In your JWT verification logic, allow for a small amount of clock skew (e.g., 60 seconds) to account for minor time differences between the server and client.
2. **Synchronize Clocks**: Ensure that the server and client clocks are synchronized, either manually or using a time synchronization protocol like NTP.

To resolve clock skew issues, adjust the clock skew tolerance in your JWT verification logic and ensure that the server and client clocks are synchronized.

### "wrong algorithm" Error

The `"wrong algorithm"` error occurs when the JWT is signed with a different algorithm than the one expected by the verification logic.

1. **Verify Signing Algorithm**: Ensure that the signing algorithm (e.g., HS256, RS256) used to generate the JWT matches the one expected by the verification logic.
2. **Update Verification Logic**: If the signing algorithm has changed, update the verification logic to use the correct algorithm.

To fix this error, verify the signing algorithm and update the verification logic accordingly.

### Missing Bearer Prefix

When sending a JWT in the `Authorization` header, the token should be prefixed with the `Bearer` keyword. If this prefix is missing, the server may reject the request.

1. **Add Bearer Prefix**: Ensure that the `Authorization` header is correctly formatted as `Authorization: Bearer <token>`.
2. **Update Client Code**: Update the client-side code to include the `Bearer` prefix when sending the JWT in the `Authorization` header.

To resolve this issue, add the `Bearer` prefix to the `Authorization` header when sending the JWT.

### CORS Issues with Authorization Header

If your application is running on a different origin than the server, you may encounter CORS (Cross-Origin Resource Sharing) issues when sending the JWT in the `Authorization` header.

1. **Configure CORS**: Ensure that the server is properly configured to allow the client's origin to access the `Authorization` header.
2. **Update Client Code**: If necessary, update the client-side code to include the `Authorization` header in the CORS "Access-Control-Request-Headers" list.

To fix CORS issues with the `Authorization` header, configure the server's CORS settings and update the client-side code accordingly.

By following the debugging steps and code fixes outlined in this guide, you should be able to resolve the most common JWT authentication errors you may encounter.