---
title: "Kubernetes Cluster Network Topology"
description: "Kubernetes cluster network topology with CNI plugin configuration."
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

The Kubernetes cluster uses a Calico CNI plugin with BGP routing between nodes. Pod-to-pod communication uses an overlay network with VXLAN encapsulation.

![Kubernetes Cluster Network Topology](images/net-02.png)

## Details

Refer to the diagram above for specific configuration details, component names, and measured values.
