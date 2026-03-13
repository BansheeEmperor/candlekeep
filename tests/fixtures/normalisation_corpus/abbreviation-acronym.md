---
title: "Kubernetes Orchestration"
description: "Kubernetes cluster management, pod scheduling, and service discovery"
keywords: [kubernetes, pod, deployment, service, ingress, kubectl]
category: "infrastructure"
tags: [kubernetes, containers]
---

## Kubernetes Architecture

Kubernetes manages containerised workloads across a cluster of nodes. The control
plane components include the API server, etcd, scheduler, and controller manager.
Worker nodes run the kubelet agent and container runtime.

## Pod Scheduling

The Kubernetes scheduler assigns pods to nodes based on resource requests, node
affinity rules, and taints. Pods that cannot be scheduled remain in Pending state
until a suitable node becomes available.

## Service Discovery

Kubernetes services provide stable DNS names and IP addresses for pod groups.
The kube-proxy component programs iptables or IPVS rules to route traffic to
healthy pod endpoints. CoreDNS resolves service names within the cluster.

## Rolling Updates

Kubernetes deployments support rolling updates with configurable surge and
unavailability limits. The deployment controller replaces pods incrementally,
waiting for readiness probes before proceeding to the next batch.
