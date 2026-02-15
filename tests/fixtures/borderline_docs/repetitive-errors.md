---
title: "Error Code Reference"
description: "Standard error codes and meanings"
keywords: ["errors", "HTTP", "status codes"]
category: "design"
tags: ["errors", "api"]
---

# Error Code Reference

## Client Errors

Error 400 means Bad Request. The client sent an invalid request. Check the request body and parameters. Return a descriptive error message. Log the error for debugging. Common causes include missing required fields, invalid data types, and malformed JSON. Always validate input before processing.

Error 401 means Unauthorized. The client is not authenticated. Check the authorization header. Verify the token is valid. Return a login prompt or token refresh hint. Common causes include missing tokens, expired tokens, and invalid signatures. Do not reveal whether the user exists.

Error 403 means Forbidden. The client is authenticated but lacks permission. Check the user's roles and permissions. Return a clear access denied message. Log the access attempt. Common causes include insufficient role, resource ownership mismatch, and IP restrictions. Never expose internal permission logic.

Error 404 means Not Found. The requested resource does not exist. Check the URL path. Verify the resource ID. Return a helpful message suggesting valid endpoints. Common causes include typos in URLs, deleted resources, and incorrect IDs. Consider returning suggestions for similar resources.

Error 409 means Conflict. The request conflicts with the current state. Check for duplicate entries. Verify optimistic locking versions. Return details about the conflict. Common causes include duplicate unique keys, concurrent modifications, and state machine violations.

Error 422 means Unprocessable Entity. The request is well-formed but semantically invalid. Check business rule validations. Return specific field-level errors. Common causes include invalid email formats, out-of-range values, and cross-field validation failures.

Error 429 means Too Many Requests. The client exceeded the rate limit. Check the rate limit headers. Wait before retrying. Implement exponential backoff in the client. Return Retry-After header. Common causes include aggressive polling, missing client-side caching, and bot traffic.

## Server Errors

Error 500 means Internal Server Error. Something went wrong on the server. Check the server logs. Alert the operations team. Return a generic error message to the client. Common causes include unhandled exceptions, database connection failures, and null pointer errors. Never expose stack traces.

Error 502 means Bad Gateway. The upstream server returned an invalid response. Check the upstream service health. Verify network connectivity. Retry the request after a delay. Common causes include upstream deployments, network partitions, and DNS resolution failures.

Error 503 means Service Unavailable. The server is temporarily overloaded. Check the server load and capacity. Scale up if needed. Return a retry-after header to the client. Common causes include traffic spikes, resource exhaustion, and dependency failures. Implement circuit breakers.

Error 504 means Gateway Timeout. The upstream server did not respond in time. Check upstream latency. Increase timeout settings if appropriate. Consider async processing for long operations. Common causes include slow database queries, external API latency, and network congestion.
