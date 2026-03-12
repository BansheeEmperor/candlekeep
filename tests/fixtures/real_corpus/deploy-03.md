---
title: "Search Service Deployment"
description: "Elasticsearch cluster deployment topology for the search service."
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

The search service uses a dedicated Elasticsearch cluster with separate master, data, and coordinating nodes. The cluster is deployed behind a dedicated load balancer.

![Search Service Deployment](images/deploy-03.png)

## Details

Refer to the diagram above for specific configuration details, component names, and measured values.
