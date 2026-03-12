---
title: "CQRS Read Model Architecture"
description: "CQRS architecture with separate read and write models for the product catalog."
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

The product catalog uses CQRS to separate write operations from read queries. Write commands update the event store, which projects into multiple optimized read models.

![CQRS Read Model Architecture](images/arch-02.png)

## Details

Refer to the diagram above for specific configuration details, component names, and measured values.
