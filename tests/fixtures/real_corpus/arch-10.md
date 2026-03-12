---
title: "API Rate Limiting Architecture"
description: "Token bucket rate limiting architecture for the public API."
keywords:
  - architecture
  - diagram
  - technical
category: "architecture"
tags:
  - visual
  - benchmark
---

## Overview

The API rate limiting system uses a token bucket algorithm with per-customer quotas stored in Redis. Quota enforcement happens at the API gateway layer.

![API Rate Limiting Architecture](images/arch-10.png)

## Details

Refer to the diagram above for specific configuration details, component names, and measured values.
