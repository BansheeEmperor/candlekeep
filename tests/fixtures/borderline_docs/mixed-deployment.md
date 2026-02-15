---
title: "Deployment Practices"
description: "Deployment strategies and practices"
keywords: ["deployment", "CI/CD", "rollback", "blue-green"]
category: "operations"
tags: ["deployment", "ops"]
---

# Deployment Practices

## Blue-Green Deployment

Maintain two identical production environments: blue (current) and green (new). Deploy the new version to the idle environment. Run smoke tests against the green environment. Switch the load balancer to point traffic to green. If something goes wrong, switch back to blue immediately — rollback is instant because the old environment is still running. The key advantage over in-place deployment is zero-downtime releases and instant rollback without redeployment.

The cost is double the infrastructure during the transition window. For stateful services, you also need to handle database migrations carefully — the schema must be compatible with both versions during the switchover period.

## Canary Deployment

Route a small percentage of traffic to the new version. Monitor error rates and latency. Gradually increase traffic if metrics look good.

## Rolling Deployment

Update instances one at a time. Simple but slow rollback.

## Feature Flags

TODO: Write section on feature flag strategies and tools.
