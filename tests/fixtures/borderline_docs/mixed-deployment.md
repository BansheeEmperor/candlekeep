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

The cost is double the infrastructure during the transition window. For stateful services, you also need to handle database migrations carefully — the schema must be compatible with both versions during the switchover period. Blue-green works best for stateless services with backward-compatible database changes.

## Canary Deployment

Route a small percentage of traffic to the new version. Monitor error rates and latency. Gradually increase traffic if metrics look good. Roll back immediately if anomalies appear. Canary deployments reduce blast radius. Start with 1-5% of traffic. Use automated analysis to detect regressions. Canary is safer than blue-green for large-scale services.

## Rolling Deployment

Update instances one at a time. Each instance is taken out of the load balancer, updated, health-checked, and returned. Simple to implement. Rollback requires re-deploying the old version to each instance. Slower rollback than blue-green. Works well for stateless services with many instances.

## Feature Flags

Decouple deployment from release. Deploy code with features disabled. Enable features gradually using configuration. Feature flags allow testing in production. Use them for A/B testing, gradual rollouts, and kill switches. Clean up old flags regularly to avoid technical debt. Feature flags are important for modern deployment practices.

## Rollback Strategy

Every deployment needs a rollback plan. Test rollback procedures regularly. Automate rollback triggers based on error rate thresholds. Keep the previous version available for quick revert. Document rollback steps for manual intervention. Rollback should be faster than deployment.
