---
title: API Gateway Patterns and Best Practices
description: A comprehensive guide to API gateway design patterns, including rate limiting, authentication, request routing, response aggregation, and circuit breaking.
keywords: 
  - api gateway
  - rate limiting
  - authentication
  - request routing
  - response aggregation
  - circuit breaking
category: architecture
tags:
  - api
  - microservices
  - patterns
  - best practices
---

## API Gateway Patterns

An API gateway is a server that acts as an entry point for a client application to access data or functionality provided by a set of microservices. The gateway handles tasks such as request/response routing, protocol translation, caching, and security. Common API gateway design patterns include:

### Proxy Pattern
The proxy pattern is the simplest API gateway implementation, where the gateway forwards requests directly to the appropriate microservice without any additional processing. This pattern is suitable for simple use cases where the gateway does not need to perform complex transformations or aggregations.

#### Example Configuration
```yaml
routes:
  - path: /users
    target: users-service
  - path: /products
    target: products-service
```

### Aggregator Pattern
The aggregator pattern is used when a client needs to retrieve data from multiple microservices. The API gateway is responsible for sending the individual requests to the relevant services, aggregating the responses, and returning the combined result to the client.

#### Example Architecture
![Aggregator Pattern Diagram](https://example.com/aggregator-pattern.png)

```yaml
routes:
  - path: /orders
    target: 
      - orders-service
      - customers-service
      - products-service
    response_aggregation:
      type: merge
      fields:
        - order_id
        - customer_name
        - product_name
        - quantity
        - total_price
```

### Translator Pattern
The translator pattern is used when the client and microservice APIs have different data formats or protocols. The API gateway is responsible for translating the client's request into the format expected by the microservice, and then translating the response back into the client's expected format.

#### Example Configuration
```yaml
routes:
  - path: /v1/books
    target: books-service
    request_translation:
      type: json-to-xml
    response_translation: 
      type: xml-to-json
```

### Decomposer Pattern
The decomposer pattern is used when a client request requires data from multiple microservices, but the client does not want to be responsible for orchestrating those requests. The API gateway is responsible for decomposing the client's request into individual service calls, executing them concurrently, and then composing the final response.

#### Example Architecture
![Decomposer Pattern Diagram](https://example.com/decomposer-pattern.png)

```yaml
routes:
  - path: /product/{id}
    target:
      - product-service
      - inventory-service
      - reviews-service
    response_aggregation:
      type: merge
      fields:
        - product_id
        - name
        - description
        - price
        - quantity
        - rating
        - num_reviews
```

## Rate Limiting

Rate limiting is a technique used to control the number of requests a client can make to an API within a given time period. This is important for protecting the API from abuse, ensuring fair usage, and managing resource consumption.

### Token Bucket Algorithm
The token bucket algorithm is a common approach to implementing rate limiting. It works by maintaining a "bucket" that holds a certain number of "tokens". Clients must "spend" a token for each request they make. The bucket is refilled at a fixed rate, allowing clients to burst above the limit for short periods of time.

#### Example Configuration
```yaml
rate_limiting:
  enabled: true
  algorithm: token-bucket
  config:
    bucket_size: 100
    refill_rate: 10 # tokens per second
```

### Leaky Bucket Algorithm
The leaky bucket algorithm is another approach to rate limiting. It works by maintaining a queue of requests, and only allowing a fixed number of requests to be processed per unit of time. Any requests that exceed the rate limit are dropped.

#### Example Configuration
```yaml
rate_limiting:
  enabled: true
  algorithm: leaky-bucket
  config:
    max_queue_size: 50
    processing_rate: 20 # requests per second
```

### Per-Client Rate Limiting
In addition to global rate limiting, it's also common to apply rate limits on a per-client basis. This allows the API gateway to enforce different limits for different types of clients (e.g. free vs paid users).

#### Example Configuration
```yaml
rate_limiting:
  enabled: true
  algorithm: token-bucket
  config:
    default_bucket_size: 100
    default_refill_rate: 10
    client_overrides:
      - client_id: abc123
        bucket_size: 500
        refill_rate: 50
      - client_id: xyz456 
        bucket_size: 50
        refill_rate: 5
```

## Authentication and Authorization

The API gateway is responsible for handling authentication and authorization for incoming requests. This ensures that only authorized clients can access the underlying microservices.

### API Key Authentication
API key authentication is a simple method where clients include a unique API key in their requests. The gateway validates the API key and forwards the request to the appropriate service.

#### Example Configuration
```yaml
authentication:
  type: api-key
  config:
    header_name: X-API-Key
    verification:
      type: db-lookup
      db_connection: postgres://user:pass@example.com/apikeys
      query: SELECT * FROM api_keys WHERE key = :key
```

### OAuth 2.0
OAuth 2.0 is a popular authentication standard that allows clients to obtain limited access to HTTP services on behalf of a resource owner. The API gateway can handle the OAuth flow, validating access tokens and forwarding requests to the appropriate services.

#### Example Configuration
```yaml
authentication:
  type: oauth2
  config:
    authorization_endpoint: https://auth.example.com/oauth/authorize
    token_endpoint: https://auth.example.com/oauth/token
    introspection_endpoint: https://auth.example.com/oauth/introspect
    required_scopes:
      - read:products
      - write:orders
```

### JSON Web Tokens (JWT)
JSON Web Tokens (JWT) are a compact, URL-safe means of representing claims to be transferred between two parties. The API gateway can validate JWT tokens and extract the necessary claims to authorize the request.

#### Example Configuration
```yaml
authentication:
  type: jwt
  config:
    issuer: https://auth.example.com
    audience: api.example.com
    required_claims:
      - sub
      - email
      - role
    verification:
      type: public-key
      key: |
        -----BEGIN PUBLIC KEY-----
        MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAy8Ac1e+/fhSlmD0HyN3Q
        ...
        -----END PUBLIC KEY-----
```

## Request Routing

The API gateway is responsible for routing incoming requests to the appropriate microservice. This can involve path-based routing, content-based routing, or a combination of both.

### Path-Based Routing
Path-based routing is the simplest form of request routing, where the gateway forwards requests based on the URL path.

#### Example Configuration
```yaml
routes:
  - path: /users
    target: users-service
  - path: /products
    target: products-service
  - path: /orders
    target: orders-service
```

### Content-Based Routing
Content-based routing allows the gateway to make routing decisions based on the request payload or headers, in addition to the URL path.

#### Example Configuration
```yaml
routes:
  - path: /transactions
    target: 
      - transactions-service
      - payments-service
    condition:
      type: header
      name: X-Transaction-Type
      value: payment
  - path: /transactions
    target: transactions-service
    condition:
      type: body
      json_path: $.type
      value: refund
```

### Dynamic Routing
Dynamic routing allows the gateway to make routing decisions based on runtime data, such as service health or load. This can be used to implement advanced load balancing or failover strategies.

#### Example Configuration
```yaml
routes:
  - path: /products
    target: 
      - product-service-1
      - product-service-2
      - product-service-3
    load_balancing:
      type: round-robin
  - path: /orders
    target:
      - order-service-1
      - order-service-2
    health_check:
      type: http
      path: /healthz
      interval: 10s
      timeout: 2s
```

## Response Aggregation

When a client request requires data from multiple microservices, the API gateway can be responsible for aggregating the individual responses into a single, combined response.

### Merge Aggregation
Merge aggregation combines the responses from multiple services into a single response, merging the data based on a set of common fields.

```yaml
routes:
  - path: /orders
    target:
      - orders-service
      - customers-service
      - products-service
    response_aggregation:
      type: merge
      fields:
        - order_id
        - customer_name
        - product_name
        - quantity
        - total_price
```

### Waterfall Aggregation
Waterfall aggregation is a sequential process where the gateway makes a series of requests to different services, with each response informing the next request.

```yaml
routes:
  - path: /product/{id}
    target:
      - product-service
      - inventory-service
      - reviews-service
    response_aggregation:
      type: waterfall
      steps:
        - service: product-service
          fields: 
            - product_id
            - name
            - description
            - price
        - service: inventory-service
          fields:
            - quantity
        - service: reviews-service
          fields:
            - rating
            - num_reviews
```

### Parallel Aggregation
Parallel aggregation sends requests to multiple services concurrently, and then combines the responses into a single result.

```yaml
routes:
  - path: /user/{id}
    target:
      - user-service
      - profile-service
      - preferences-service
    response_aggregation:
      type: parallel
      fields:
        - user_id
        - username
        - email
        - profile_image
        - theme
        - language
```

## Circuit Breaking

Circuit breaking is a pattern used to detect failures and avoid cascading failures in distributed systems. The API gateway can implement circuit breaking to protect the underlying microservices from being overwhelmed by failed or slow requests.

### Netflix Hystrix
Hystrix is a popular open-source library for implementing the circuit breaker pattern. It provides a simple API for wrapping service calls and monitoring their behavior.

```java
@HystrixCommand(fallbackMethod = "getProductFallback")
public Product getProduct(String id) {
    return productService.getProduct(id);
}

private Product getProductFallback(String id) {
    return new Product("Unknown", 0.0, "Fallback product");
}
```

### Bulkhead Pattern
The bulkhead pattern is a variation of the circuit breaker, where the gateway maintains separate resource pools for each downstream service. This prevents a single failing service from affecting the others.

```yaml
circuit_breaking:
  enabled: true
  config:
    - service: users-service
      max_concurrent_requests: 50
      timeout: 2s
    - service: products-service 
      max_concurrent_requests: 100
      timeout: 5s
    - service: orders-service
      max_concurrent_requests: 30
      timeout: 3s
```

### Adaptive Thresholds
Instead of using static thresholds for circuit breaking, the gateway can dynamically adjust the thresholds based on observed performance and load. This allows the circuit breaker to be more responsive to changing conditions.

```yaml
circuit_breaking:
  enabled: true
  config:
    - service: users-service
      detection:
        type: adaptive
        min_request_volume: 20
        error_percentage_threshold: 50%
        latency_threshold: 
          value: 500ms
          measurement: p99
    - service: products-service
      detection:
        type: adaptive
        min_request_volume: 50
        error_percentage_threshold: 30%
        latency_threshold:
          value: 1s
          measurement: p95
```

By implementing these API gateway patterns and best practices, you can build a robust and scalable microservices architecture that addresses common challenges such as load balancing, fault tolerance, and cross-cutting concerns.