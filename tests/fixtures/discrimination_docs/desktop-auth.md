---
title: Desktop Authentication Guide
description: Implementing Windows Hello and token-based auth for Desktop apps using Electron.
category: authentication
tags: desktop, electron, windows
---
# Desktop Authentication

For desktop applications built with Electron, you can leverage native OS capabilities like Windows Hello.
Use the `node-ffi` or similar bridges to call Win32 APIs for biometric verification.

```javascript
// Example calling native biometric check
const isVerified = nativeModule.verifyWindowsHello();
if (isVerified) {
    // Grant access
}
```

Store tokens in the system's native secure vault. On Windows, this is the Credential Manager.
On macOS, use the Keychain. Avoid using plain files in the user's home directory.
Encrypt your application data using a key tied to the user's OS account.
