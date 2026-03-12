---
title: "Secret Rotation Incident Timeline"
description: "Timeline of the secret rotation failure incident on 2024-11-14."
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

An automated secret rotation job failed to update the database credentials in all services. Several services began failing with authentication errors after the old credentials expired.

![Secret Rotation Incident Timeline](images/inc-09.png)

## Details

Refer to the diagram above for specific configuration details, component names, and measured values.
