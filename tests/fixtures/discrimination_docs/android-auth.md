---
title: Android Authentication Guide
description: Implementing biometric and token-based auth for Android apps using Kotlin.
category: authentication
tags: android, kotlin, mobile
---
# Android Authentication

On Android, use the BiometricPrompt API for secure user verification.
This provides a consistent UI across different device manufacturers.

```kotlin
val biometricPrompt = BiometricPrompt(activity, executor, callback)
val promptInfo = BiometricPrompt.PromptInfo.Builder()
    .setTitle("Biometric login")
    .setSubtitle("Log in using your biometric credential")
    .setNegativeButtonText("Use account password")
    .build()
```

For secure storage, use the Android Keystore system. EncryptedSharedPreferences is the recommended way to store small bits of sensitive data like JWTs.
Ensure your master key is stored in the Keystore.
