---
title: "VPC Network Topology"
description: "AWS VPC network topology for the production environment."
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

The production environment uses a multi-AZ VPC with public and private subnets. Network traffic flows through NAT gateways and a transit gateway for cross-VPC communication.

![VPC Network Topology](images/net-01.png)

## Details

Refer to the diagram above for specific configuration details, component names, and measured values.
