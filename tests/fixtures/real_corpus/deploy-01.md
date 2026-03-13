---
title: "Authentication Service Deployment"
description: "Multi-region deployment topology for the authentication service."
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

The authentication service is deployed across two availability zones in a primary region with a warm standby in a secondary region. The topology uses an active-active configuration with session replication.

![Authentication Service Deployment](images/deploy-01.png)

## Details

Refer to the diagram above for specific configuration details, component names, and measured values.
