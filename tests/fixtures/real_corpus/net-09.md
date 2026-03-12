---
title: "Container Network Topology"
description: "Docker Swarm overlay network topology for the microservices cluster."
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

The Docker Swarm cluster uses overlay networks to isolate service communication. Frontend services communicate with backend services through a dedicated overlay network.

![Container Network Topology](images/net-09.png)

## Details

Refer to the diagram above for specific configuration details, component names, and measured values.
