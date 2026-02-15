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

Use a time-series database like Prometheus or InfluxDB to store metrics. Scrape metrics at 15-second intervals for real-time dashboards. Retain high-resolution data for 7 days and downsample to 1-minute intervals for long-term storage.

## Alerting

TODO: Write alerting section.

## Dashboards

Dashboards are useful. Create dashboards for your services. Use Grafana or similar tools.

## Log Aggregation

TODO: Expand this section with ELK stack details and structured logging patterns.
