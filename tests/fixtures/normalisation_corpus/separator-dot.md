---
title: "Semantic Versioning"
description: "Version numbering with major.minor.patch and pre-release identifiers"
keywords: [semver, major.minor.patch, v1.0.0, versioning]
category: "engineering"
tags: [semver, versioning]
---

## Semantic Versioning Format

Semantic versioning uses a major.minor.patch format. A version like v1.4.2 means
major version 1, minor version 4, patch version 2. The major.minor.patch scheme
communicates the nature of changes to consumers.

## Breaking Changes

Incrementing the major component signals breaking changes. Consumers pinned to
v1.x.x must explicitly upgrade to v2.0.0. The major.minor.patch contract lets
dependency managers resolve compatible versions automatically.

## Pre-Release Identifiers

Pre-release versions append identifiers after the patch: v1.0.0-alpha.1,
v1.0.0-beta.2, v1.0.0-rc.1. These sort before the release version and signal
instability to consumers.

## Lock Files

Lock files pin exact versions including the full major.minor.patch string.
This ensures reproducible builds across environments regardless of registry
updates or yanked versions.
