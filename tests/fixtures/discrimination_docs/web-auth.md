---
title: Web Authentication Guide
description: Implementing OAuth2 and session-based auth for Web applications using React.
category: authentication
tags: web, react, oauth2
---
# Web Authentication

For web apps, the industry standard is OAuth 2.0 with OpenID Connect.
Use the Authorization Code Flow with PKCE for single-page applications (SPAs).

```javascript
const oauthConfig = {
  client_id: 'your-id',
  redirect_uri: 'https://app.com/callback',
  response_type: 'code',
  scope: 'openid profile'
};
```

Store your tokens in HttpOnly, Secure cookies to prevent XSS attacks.
Avoid storing sensitive tokens in localStorage or sessionStorage as they are accessible by any script running on your page.
Use a SameSite=Strict attribute for maximum CSRF protection.
