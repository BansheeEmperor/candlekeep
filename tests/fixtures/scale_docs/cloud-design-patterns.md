---
title: Cloud Design Patterns for Resilient Applications
description: Detailed technical documentation for implementing common cloud design patterns like retry, circuit breaker, bulkhead, throttling, queue-based load leveling, and competing consumers.
keywords: 
  - cloud design patterns
  - resilient applications
  - retry
  - circuit breaker
  - bulkhead
  - throttling
  - queue-based load leveling
  - competing consumers
category: cloud architecture
tags:
  - cloud
  - design patterns
  - resilience
  - scalability
  - availability
---

## Retry Pattern

The Retry pattern is used to handle transient failures when invoking a service or accessing a resource. When a failure occurs, the pattern retries the operation a configured number of times with a wait period between each attempt. This can help overcome temporary issues like network failures, service interruptions, or high request volumes.

### Implementing Retry in .NET

In .NET, the Polly library provides a simple way to implement the Retry pattern. Here's an example:

```csharp
// Create a retry policy
var retryPolicy = Policy.Handle<SomeException>()
    .Retry(3, (exception, retryCount) =>
    {
        // Log the exception and retry count
        Console.WriteLine($"Retry attempt {retryCount} failed due to: {exception}");
    });

// Use the policy to execute an operation
var result = retryPolicy.Execute(() =>
{
    // Potentially failing operation
    return DoSomeWork();
});
```

In this example, the `Retry` method specifies that the operation should be retried up to 3 times if a `SomeException` is thrown. The second parameter is a callback that allows you to log or handle the exception on each retry attempt.

The `retryPolicy.Execute()` method wraps the potentially failing operation and handles the retrying logic.

### Configuring Retry Policies

Retry policies can be configured with various options:

- `Retry(retryCount)`: Specifies the maximum number of retry attempts.
- `WaitAndRetry(retryCount, sleepDurationProvider)`: Allows you to specify a custom wait time between each retry attempt.
- `WaitAndRetryForever(sleepDurationProvider)`: Retries the operation indefinitely until it succeeds.
- `RetryAsync(retryCount)`: Provides an asynchronous version of the Retry policy.

The `sleepDurationProvider` parameter is a function that calculates the wait time for each retry attempt, for example:

```csharp
var retryPolicy = Policy.Handle<SomeException>()
    .WaitAndRetry(3, retryAttempt => TimeSpan.FromSeconds(Math.Pow(2, retryAttempt)));
```

This implements an exponential backoff strategy, where the wait time doubles with each retry attempt.

### Handling Different Exceptions

The Retry pattern can be configured to handle different types of exceptions. In the example above, we're only retrying on `SomeException`, but you can specify multiple exception types:

```csharp
var retryPolicy = Policy.Handle<SomeException>()
    .Or<AnotherException>()
    .Retry(3);
```

This policy will retry the operation if either `SomeException` or `AnotherException` is thrown.

### Applying Retry Policies

Retry policies can be applied at various levels in your application, such as:

- At the individual method or operation level
- At the service or client level, to handle failures when calling external services
- At the application or entry point level, to handle overall application failures

Applying the policy at a higher level can provide more comprehensive failure handling, but it's important to balance the tradeoffs between centralized and decentralized retry logic.

## Circuit Breaker Pattern

The Circuit Breaker pattern is used to handle failures in remote procedure calls or service invocations. It acts as a circuit breaker, which trips and "opens" the circuit when a certain number of failures occur within a time period, temporarily preventing further calls to the failing service. This can help prevent cascading failures in a distributed system.

### Implementing Circuit Breaker in .NET

In .NET, the Polly library also provides a Circuit Breaker implementation:

```csharp
// Create a circuit breaker policy
var circuitBreakerPolicy = Policy.Handle<SomeException>()
    .CircuitBreaker(
        exceptionsAllowedBeforeBreaking: 2,
        durationOfBreak: TimeSpan.FromSeconds(30),
        onBreak: (ex, breakDelay) =>
        {
            // Log the circuit breaker opening
            Console.WriteLine($"Circuit breaker opened due to {ex.GetType().Name}. Breaker will be closed after {breakDelay.TotalSeconds} seconds.");
        },
        onReset: () =>
        {
            // Log the circuit breaker closing
            Console.WriteLine("Circuit breaker closed. Allowing operations to proceed.");
        });

// Use the policy to execute an operation
var result = circuitBreakerPolicy.Execute(() =>
{
    // Potentially failing operation
    return DoSomeWork();
});
```

In this example, the `CircuitBreaker` method specifies that the circuit will be opened after 2 exceptions of type `SomeException` are encountered within a certain time period. The circuit will remain open for 30 seconds, during which time all calls to the service will fail immediately. The `onBreak` and `onReset` callbacks allow you to log or handle the circuit breaker state changes.

The `circuitBreakerPolicy.Execute()` method wraps the potentially failing operation and handles the circuit breaker logic.

### Circuit Breaker States

The Circuit Breaker pattern has three main states:

1. **Closed**: The circuit is closed, and requests are allowed to pass through normally.
2. **Open**: The circuit is open, and all requests fail immediately.
3. **Half-Open**: The circuit is in a testing state, allowing a limited number of requests to pass through to see if the underlying service has recovered.

The transition between these states is controlled by the configured thresholds and timers.

### Configuring Circuit Breaker Policies

The Circuit Breaker policy can be configured with the following options:

- `CircuitBreaker(exceptionsAllowedBeforeBreaking, durationOfBreak, onBreak, onReset)`: Specifies the number of exceptions allowed before the circuit is opened, the duration the circuit remains open, and callbacks for handling the circuit state changes.
- `CircuitBreakerAsync(exceptionsAllowedBeforeBreaking, durationOfBreak, onBreak, onReset)`: Provides an asynchronous version of the Circuit Breaker policy.
- `AdvancedCircuitBreaker(exceptionsAllowedBeforeBreaking, millisecondsDurationOfBreak, sleepDurationProvider, onBreak, onReset)`: Allows more advanced configuration, such as a custom sleep duration provider.

The `sleepDurationProvider` parameter is a function that calculates the duration the circuit should remain open before transitioning to the Half-Open state.

### Applying Circuit Breaker Policies

Circuit Breaker policies can be applied in a similar way to Retry policies, at the method, service, or application level. It's common to combine Retry and Circuit Breaker policies, where the Retry policy is used within the Circuit Breaker to handle transient failures, and the Circuit Breaker is used to protect the system from cascading failures.

## Bulkhead Pattern

The Bulkhead pattern is used to isolate parts of an application to limit the impact of failures. It separates the application into different contexts or "bulkheads", so that a failure in one part of the system does not affect the entire application.

### Implementing Bulkhead in .NET

In .NET, the Polly library provides a Bulkhead implementation:

```csharp
// Create a bulkhead policy
var bulkheadPolicy = Policy.Bulkhead(
    maxParallelization: 10,
    maxQueueSize: 20,
    onBulkheadRejected: (context) =>
    {
        // Log the bulkhead rejection
        Console.WriteLine($"Bulkhead rejected execution of {context.OperationKey}");
    });

// Use the policy to execute an operation
var result = bulkheadPolicy.Execute(() =>
{
    // Potentially resource-intensive operation
    return DoSomeWork();
});
```

In this example, the `Bulkhead` method specifies that the maximum number of concurrent executions is 10, and the maximum queue size is 20. If the bulkhead is full, additional requests will be rejected, and the `onBulkheadRejected` callback will be called.

The `bulkheadPolicy.Execute()` method wraps the potentially resource-intensive operation and handles the bulkhead logic.

### Bulkhead Configuration

The Bulkhead policy can be configured with the following options:

- `Bulkhead(maxParallelization, maxQueueSize, onBulkheadRejected)`: Specifies the maximum number of concurrent executions, the maximum queue size, and a callback for handling rejected executions.
- `BulkheadAsync(maxParallelization, maxQueueSize, onBulkheadRejected)`: Provides an asynchronous version of the Bulkhead policy.

The `onBulkheadRejected` callback allows you to log or handle the rejected executions, which can be important for monitoring and alerting.

### Applying Bulkhead Policies

Bulkhead policies can be applied at various levels in your application, such as:

- At the individual method or operation level, to isolate resource-intensive operations
- At the service or client level, to isolate calls to external services
- At the application or entry point level, to provide a global bulkhead for the entire application

Applying the policy at a higher level can provide more comprehensive isolation, but it's important to balance the tradeoffs between centralized and decentralized bulkhead management.

## Throttling Pattern

The Throttling pattern is used to control the consumption of resources shared by multiple consumers. It limits the rate at which a consumer can access a service or resource, preventing overload and ensuring fair access for all consumers.

### Implementing Throttling in .NET

In .NET, the Polly library provides a Throttling implementation:

```csharp
// Create a throttling policy
var throttlingPolicy = Policy.Throttle(
    "my-operation",
    perSecondLimit: 10,
    fetcherForLimitContext: (context) => Task.FromResult(10),
    onRateBreached: (context, limit, timestamp) =>
    {
        // Log the rate breach
        Console.WriteLine($"Rate limit of {limit} per second exceeded for operation {context.OperationKey}");
    });

// Use the policy to execute an operation
var result = throttlingPolicy.Execute(() =>
{
    // Potentially high-volume operation
    return DoSomeWork();
});
```

In this example, the `Throttle` method specifies that the maximum number of executions for the "my-operation" key is 10 per second. The `fetcherForLimitContext` parameter is a function that fetches the current rate limit for the operation, which can be dynamic based on the context.

The `onRateBreached` callback is called when the rate limit is exceeded, allowing you to log or handle the breach.

The `throttlingPolicy.Execute()` method wraps the potentially high-volume operation and handles the throttling logic.

### Throttling Configuration

The Throttling policy can be configured with the following options:

- `Throttle(operationKey, perSecondLimit, fetcherForLimitContext, onRateBreached)`: Specifies the operation key, the rate limit per second, a function to fetch the current rate limit, and a callback for handling rate breaches.
- `ThrottleAsync(operationKey, perSecondLimit, fetcherForLimitContext, onRateBreached)`: Provides an asynchronous version of the Throttling policy.

The `fetcherForLimitContext` parameter is a function that can dynamically fetch the current rate limit based on the context, which can be useful for scenarios where the limit may change over time or based on other factors.

### Applying Throttling Policies

Throttling policies can be applied at various levels in your application, such as:

- At the individual method or operation level, to limit the rate of specific operations
- At the service or client level, to limit the rate of calls to external services
- At the application or entry point level, to provide a global throttling mechanism for the entire application

Applying the policy at a higher level can provide more comprehensive throttling, but it's important to balance the tradeoffs between centralized and decentralized throttling management.

## Queue-based Load Leveling Pattern

The Queue-based Load Leveling pattern is used to smooth out high volumes of requests or tasks by placing them in a queue. This allows the system to handle bursts of activity without overloading the downstream components.

### Implementing Queue-based Load Leveling in Azure

In Azure, you can use Azure Storage Queues or Azure Service Bus Queues to implement the Queue-based Load Leveling pattern. Here's an example using Azure Storage Queues:

```csharp
// Create a queue client
var queueClient = new QueueClient(connectionString, queueName);

// Send a message to the queue
var message = new QueueMessage(JsonSerializer.Serialize(myData));
await queueClient.SendMessageAsync(message);

// Process messages from the queue
while (true)
{
    var messages = await queueClient.ReceiveMessagesAsync(maxMessages: 10, visibilityTimeout: TimeSpan.FromSeconds(30));
    foreach (var message in messages)
    {
        // Process the message
        var data = JsonSerializer.Deserialize<MyData>(message.Body);
        // ...
        
        // Complete the message
        await queueClient.CompleteMessageAsync(message);
    }
}
```

In this example, we're using the Azure Storage Queues client library to send a message to a queue and then process messages from the queue. The `ReceiveMessagesAsync` method allows us to retrieve up to 10 messages at a time, with a visibility timeout of 30 seconds. This gives the processing logic time to complete before the message becomes visible again.

The queue acts as a buffer between the producer and the consumer, allowing the system to handle bursts of activity without overloading the downstream components.

### Configuring Queue-based Load Leveling

When configuring a Queue-based Load Leveling solution, you'll need to consider the following factors:

- **Queue size**: Determine the appropriate queue size based on the expected volume of requests and the processing capacity of the downstream components.
- **Visibility timeout**: Set the visibility timeout to a value that allows the consumer to process the message within the allotted time.
- **Batching**: Retrieve and process messages in batches to improve throughput and efficiency.
- **Poison messages**: Implement error handling and retry logic to deal with messages that cannot be successfully processed.
- **Monitoring and scaling**: Monitor the queue size and processing time, and scale the system as needed to maintain the desired level of performance.

### Applying Queue-based Load Leveling

The Queue-based Load Leveling pattern can be applied in a variety of scenarios, such as:

- **Web applications**: Use a queue to handle bursts of user requests, preventing the web application from becoming overloaded.
- **Background tasks**: Use a queue to manage the execution of long-running or resource-intensive tasks, ensuring that they don't overwhelm the system.
- **Microservices**: Use a queue to decouple services and smooth out the flow of data between them, preventing one service from overwhelming another.

By implementing the Queue-based Load Leveling pattern, you can improve the reliability, scalability, and performance of your cloud-based applications.

## Competing Consumers Pattern

The Competing Consumers pattern is used to allow multiple concurrent consumers to process messages from a queue or message broker. This can help improve the throughput and scalability of a system that needs to process a high volume of messages.

### Implementing Competing Consumers in Azure

In Azure, you can use Azure Service Bus Queues or Azure Service Bus Topics to implement the Competing Consumers pattern. Here's an example using Azure Service Bus Queues:

```csharp
// Create a queue client
var queueClient = new QueueClient(connectionString, queueName);

// Create multiple consumers
for (int i = 0; i < 5; i++)
{
    new Task(async () =>
    {
        while (true)
        {
            // Receive a message from the queue
            var message = await queueClient.ReceiveMessageAsync();
            if (message != null)
            {
                // Process the message
                var data = JsonSerializer.Deserialize<MyData>(message.Body);
                // ...
                
                // Complete the message
                await queueClient.CompleteMessageAsync(message);
            }
            else
            {
                // No messages available, wait for a short time before trying again
                await Task.Delay(1000);
            }
        }
    }).Start();
}
```

In this example, we're creating five consumer tasks