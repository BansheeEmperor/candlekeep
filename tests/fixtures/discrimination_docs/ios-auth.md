---
title: iOS Authentication Guide
description: Implementing biometric and token-based auth for iOS apps using Swift.
category: authentication
tags: ios, swift, mobile
---
# iOS Authentication

To implement authentication on iOS, use the LocalAuthentication framework. 
This allows for FaceID and TouchID integration.

```swift
let context = LAContext()
var error: NSError?
if context.canEvaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, error: &error) {
    // Proceed with biometrics
}
```

For token storage, use the iOS Keychain Services. Never store JWTs in UserDefaults as they are not encrypted.
Always ensure the `kSecClass` is set correctly to `kSecClassGenericPassword`.
