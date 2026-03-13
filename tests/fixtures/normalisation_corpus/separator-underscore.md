---
title: "API Key Authentication"
description: "Managing api_key credentials and redirect_uri validation in OAuth flows"
keywords: [api_key, redirect_uri, client_id, access_token, oauth]
category: "security"
tags: [api_key, oauth]
---

## API Key Management

An api_key is a credential issued to a client application. The api_key is passed
in request headers or query parameters to authenticate API calls. Unlike user
credentials, an api_key identifies the application, not the user.

## Redirect URI Validation

The redirect_uri parameter in OAuth flows specifies where the authorization server
sends the user after granting access. The redirect_uri must exactly match a
pre-registered value to prevent open redirect attacks.

## Client ID and Secret

The client_id identifies the application in OAuth. The client_secret is a
confidential credential known only to the application and authorization server.
The client_id is public; the client_secret must never be exposed.

## Access Token Lifecycle

An access_token is short-lived. The refresh_token allows obtaining a new
access_token without re-authenticating the user. Token rotation improves security
by limiting the window of exposure for any single access_token.
