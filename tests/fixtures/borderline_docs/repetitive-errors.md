---
title: "Error Code Reference"
description: "Standard error codes and meanings"
keywords: ["errors", "HTTP", "status codes"]
category: "design"
tags: ["errors", "api"]
---

# Error Code Reference

## Client Errors

Error 400 means Bad Request. The client sent an invalid request. Check the request body and parameters. Return a descriptive error message. Log the error for debugging.

Error 401 means Unauthorized. The client is not authenticated. Check the authorization header. Verify the token is valid. Return a login prompt or token refresh hint.

Error 403 means Forbidden. The client is authenticated but lacks permission. Check the user's roles and permissions. Return a clear access denied message. Log the access attempt.

Error 404 means Not Found. The requested resource does not exist. Check the URL path. Verify the resource ID. Return a helpful message suggesting valid endpoints.

Error 429 means Too Many Requests. The client exceeded the rate limit. Check the rate limit headers. Wait before retrying. Implement exponential backoff in the client.

## Server Errors

Error 500 means Internal Server Error. Something went wrong on the server. Check the server logs. Alert the operations team. Return a generic error message to the client.

Error 502 means Bad Gateway. The upstream server returned an invalid response. Check the upstream service health. Verify network connectivity. Retry the request after a delay.

Error 503 means Service Unavailable. The server is temporarily overloaded. Check the server load and capacity. Scale up if needed. Return a retry-after header to the client.
