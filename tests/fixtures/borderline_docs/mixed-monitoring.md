---
title: "Monitoring and Alerting"
description: "Guide to monitoring applications and setting up alerts"
keywords: ["monitoring", "alerting", "observability", "metrics"]
category: "operations"
tags: ["monitoring", "ops"]
---

# Monitoring and Alerting

## Metrics Collection

Collect four golden signals for every service: latency, traffic, errors, and saturation. Latency measures how long requests take — track p50, p95, and p99 percentiles, not just averages. Averages hide tail latency that affects your worst-off users. Traffic measures demand on the system, typically in requests per second. Error rate is the ratio of failed requests to total requests. Saturation measures how full your resources are — CPU, memory, disk, network.

Use a time-series database like Prometheus or InfluxDB to store metrics. Scrape metrics at 15-second intervals for real-time dashboards. Retain high-resolution data for 7 days and downsample to 1-minute intervals for long-term storage. Label metrics with service name, environment, and instance ID for filtering.

## Alerting

Alerts should be actionable. If an alert fires and the on-call engineer cannot do anything about it, the alert is noise. Set thresholds based on SLOs, not arbitrary numbers. Use multi-window alerting to reduce false positives. Page on symptoms, not causes.

## Dashboards

Dashboards are useful. Create dashboards for your services. Use Grafana or similar tools. Include the four golden signals on every service dashboard.

## Log Aggregation

Logs complement metrics. Use structured logging with JSON format. Include request IDs for tracing. Ship logs to a central system. Set retention policies based on compliance requirements.

## Distributed Tracing

Tracing shows request flow across services. Instrument all service boundaries. Use trace IDs propagated through headers. Sample traces in production to manage volume. Tracing is important. Every microservice architecture needs tracing. Without tracing, debugging is difficult. Tracing helps find bottlenecks.

## Health Checks

Implement health check endpoints. Liveness checks confirm the process is running. Readiness checks confirm the service can handle traffic. Health checks should be lightweight. Do not include expensive database queries in health checks. Health checks are important for orchestration platforms.
