---
title: "Auto-Scaling Infrastructure"
description: "Auto-scaling policies, scale-out triggers, and round-robin load balancing"
keywords: [auto-scaling, scale-out, round-robin, load-balancer, read-only, opt-in]
category: "infrastructure"
tags: [auto-scaling, load-balancing]
---

## Auto-Scaling Policies

Auto-scaling adjusts capacity in response to demand. Scale-out adds instances
when CPU or request rate exceeds a threshold. Scale-in removes instances during
low-traffic periods. Auto-scaling policies define the minimum, maximum, and
desired instance counts.

## Round-Robin Load Balancing

Round-robin distributes requests evenly across healthy instances. Weighted
round-robin assigns more traffic to higher-capacity instances. Round-robin
is stateless and requires no session affinity configuration.

## Read-Only Replicas

Read-only replicas offload read traffic from the primary database. Auto-scaling
can add read-only replicas during read-heavy periods. Replication lag must be
monitored to ensure read-only replicas serve acceptably fresh data.

## Opt-In Features

Some auto-scaling behaviours are opt-in. Pre-warming, predictive scaling, and
scheduled scaling actions are opt-in features that require explicit configuration.
Opt-in features are disabled by default to avoid unexpected cost increases.
