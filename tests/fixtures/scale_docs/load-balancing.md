---
title: Load Balancing Algorithms and Concepts
description: A comprehensive technical guide to load balancing algorithms, layer 4 vs layer 7 load balancing, health checks, and session persistence.
keywords: 
  - load balancing
  - round-robin
  - least connections
  - weighted
  - ip hash
  - layer 4
  - layer 7
  - health checks
  - session persistence
category: networking
tags:
  - load balancing
  - networking
  - architecture
  - high availability
---

## Load Balancing Algorithms

Load balancing algorithms are the core logic that determines how incoming traffic is distributed across a pool of backend servers. The most common load balancing algorithms are:

### Round-Robin
Round-robin is a simple and widely used load balancing algorithm. It works by sending each new connection to the next server in the list, cycling through the entire pool. This ensures each server receives an equal number of connections.

**Example Configuration:**
```
upstream my_backend {
    server backend1.example.com;
    server backend2.example.com;
    server backend3.example.com;

    lb_method round-robin;
}
```

### Least Connections
The least connections algorithm sends each new connection to the server with the fewest number of active connections. This helps balance the load more evenly across the backend servers, especially when there is variation in server capacity or request duration.

**Example Configuration:**
```
upstream my_backend {
    server backend1.example.com;
    server backend2.example.com;
    server backend3.example.com;

    lb_method least_conn;
}
```

### Weighted
Weighted load balancing allows you to assign a weight value to each backend server. Servers with a higher weight will receive more traffic than those with a lower weight. This is useful when you have servers with different capacities or processing power.

**Example Configuration:**
```
upstream my_backend {
    server backend1.example.com weight=3;
    server backend2.example.com weight=2; 
    server backend3.example.com weight=1;

    lb_method weighted_round_robin;
}
```

### IP Hash
IP hash load balancing uses a hash of the client's IP address to determine which server the connection should be sent to. This ensures that a client is always sent to the same backend server, which is useful for maintaining session affinity.

**Example Configuration:**
```
upstream my_backend {
    server backend1.example.com;
    server backend2.example.com;
    server backend3.example.com;

    lb_method ip_hash;
}
```

## Layer 4 vs Layer 7 Load Balancing

Load balancers can operate at different layers of the OSI model, providing different capabilities and trade-offs.

### Layer 4 (L4) Load Balancing
Layer 4 load balancers operate at the transport layer, making load balancing decisions based on information like IP addresses and port numbers. They are faster and simpler, but have limited visibility into the application layer.

L4 load balancers typically use the following algorithms:
- Round-robin
- Least connections
- Source IP (similar to IP hash)

L4 load balancing is often implemented in hardware for performance reasons, such as with network switches or dedicated load balancing appliances.

**Example L4 Load Balancer Config (HAProxy):**
```
frontend web
    bind *:80
    mode tcp
    default_backend web_servers

backend web_servers
    mode tcp
    balance roundrobin
    server web1 10.0.0.1:80 check
    server web2 10.0.0.2:80 check
    server web3 10.0.0.3:80 check
```

### Layer 7 (L7) Load Balancing
Layer 7 load balancers operate at the application layer, allowing them to make more intelligent routing decisions based on application-layer protocols like HTTP. They can inspect the content of requests and responses, enabling advanced features like content-based routing, SSL termination, and application-level health checks.

L7 load balancers typically use algorithms like:
- Round-robin
- Least connections 
- URI path
- HTTP header
- Cookie

L7 load balancing is often implemented in software, such as a proxy or gateway service, to provide more flexibility and programmability.

**Example L7 Load Balancer Config (NGINX):**
```
upstream web_servers {
    server 10.0.0.1;
    server 10.0.0.2;
    server 10.0.0.3;

    # L7 load balancing based on URI path
    location / {
        proxy_pass http://web_servers;
    }

    location /api/ {
        proxy_pass http://api_servers;
    }
}
```

## Health Checks

Health checks are a critical component of load balancing, as they allow the load balancer to detect unhealthy or unresponsive backend servers and stop routing traffic to them. Load balancers typically perform health checks by periodically sending a request to each backend server and evaluating the response.

### L4 Health Checks
At layer 4, health checks are typically simple TCP connection attempts or UDP requests to verify that the backend server is listening on the expected port and responding.

**Example L4 Health Check (HAProxy):**
```
backend web_servers
    mode tcp
    balance roundrobin
    server web1 10.0.0.1:80 check
    server web2 10.0.0.2:80 check
    server web3 10.0.0.3:80 check
```

### L7 Health Checks
Layer 7 health checks allow for more sophisticated monitoring, as the load balancer can send an application-level request (e.g., HTTP GET /healthz) and inspect the response. This enables detecting issues like application failures, incorrectly configured backends, or even partial failures.

**Example L7 Health Check (NGINX):**
```
upstream web_servers {
    server 10.0.0.1 max_fails=3 fail_timeout=60s;
    server 10.0.0.2 max_fails=3 fail_timeout=60s;
    server 10.0.0.3 max_fails=3 fail_timeout=60s;

    # L7 health check using HTTP GET
    health_check uri=/healthz code=200;
}
```

## Session Persistence

Session persistence, also known as session affinity or sticky sessions, is a load balancing feature that ensures a client is consistently routed to the same backend server for the duration of a session or series of requests. This is important for applications that maintain client state on the server-side, such as shopping carts, login sessions, or other stateful workloads.

The most common session persistence methods are:

### Cookie-Based
The load balancer injects a session cookie into the client's response, which is then used to identify the appropriate backend server for subsequent requests from that client.

**Example Cookie-Based Session Persistence (NGINX):**
```
upstream web_servers {
    server 10.0.0.1;
    server 10.0.0.2;
    server 10.0.0.3;

    # Enable cookie-based session persistence
    sticky cookie sess_id expires=1h;
}
```

### Source IP (IP Hash)
As mentioned earlier, the IP hash algorithm uses a hash of the client's source IP address to determine the backend server. This ensures that requests from the same client IP are always routed to the same backend.

**Example IP Hash Session Persistence (HAProxy):**
```
backend web_servers
    mode http
    balance ip-hash
    server web1 10.0.0.1:80 check
    server web2 10.0.0.2:80 check
    server web3 10.0.0.3:80 check
```

### URL Path
Some load balancers can persist sessions based on the URL path, routing requests with the same path to the same backend server. This is useful for applications that store session data in the URL.

**Example URL Path Session Persistence (NGINX):**
```
upstream web_servers {
    server 10.0.0.1;
    server 10.0.0.2;
    server 10.0.0.3;

    # Enable session persistence based on URL path
    sticky route $request_uri;
}
```

## Load Balancing Architecture Patterns

Load balancing can be implemented in various architectural patterns to achieve different goals, such as high availability, scalability, and fault tolerance.

### Single Load Balancer
The simplest load balancing setup is a single load balancer that distributes traffic to a pool of backend servers. This is a good starting point for small to medium-sized applications, but it introduces a single point of failure.

```
       Client
         |
         v
   Load Balancer
         |
         v
   Backend Servers
```

### Redundant Load Balancers
To improve availability, you can deploy multiple load balancers in an active-passive or active-active configuration. This ensures that if one load balancer fails, the other can immediately take over without disrupting service.

```
       Client
         |
         v
 Load Balancer 1  Load Balancer 2
         |             |
         v             v
   Backend Servers
```

### Hierarchical Load Balancing
In large-scale architectures, you can use a hierarchical load balancing approach, with a global load balancer distributing traffic across multiple regional or data center-specific load balancers, which then route to the backend servers.

```
       Client
         |
         v
 Global Load Balancer
         |
         v
Regional Load Balancer 1  Regional Load Balancer 2
         |                        |
         v                        v
   Backend Servers           Backend Servers
```

### Distributed Load Balancing
Distributed load balancing involves embedding load balancing logic directly into the application servers or a service mesh, allowing for a more decentralized and scalable approach.

```
       Client
         |
         v
   Service Mesh / 
Application Servers
         |
         v
   Backend Servers
```

## Advanced Load Balancing Concepts

### Circuit Breakers
Circuit breakers are a load balancing feature that automatically detects and isolates failing backend servers, preventing cascading failures and improving overall system resilience.

### Retries and Timeouts
Load balancers can be configured to automatically retry failed requests on another backend server and set appropriate timeouts to prevent clients from waiting indefinitely for a response.

### Caching and Content Acceleration
Layer 7 load balancers can cache frequently accessed content, serve static assets directly, and optimize content delivery to improve overall application performance.

### SSL/TLS Termination
Load balancers can offload the CPU-intensive task of SSL/TLS termination from the backend servers, improving their overall efficiency.

### WAF and DDoS Protection
Some load balancers integrate web application firewalls (WAFs) and DDoS protection mechanisms to defend against common web application attacks and volumetric DDoS attacks.

## Conclusion

Load balancing is a fundamental component of modern distributed systems, enabling high availability, scalability, and fault tolerance. By understanding the various load balancing algorithms, layer 4 vs. layer 7 capabilities, health checks, and session persistence mechanisms, you can design and implement robust, resilient, and high-performing load balancing architectures to support your application's needs.