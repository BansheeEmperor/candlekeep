---
title: gRPC Technical Documentation
description: A comprehensive guide to the gRPC protocol, including protocol buffers, service definitions, streaming, deadlines, and interceptors.
keywords:
  - gRPC
  - Protocol Buffers
  - Streaming
  - Deadlines
  - Interceptors
category: Development
tags:
  - gRPC
  - Protocol Buffers
  - Service Definition
  - Streaming
  - Deadlines
  - Interceptors
---

## Protocol Buffers

Protocol Buffers (protobuf) is the interface definition language used by gRPC to describe the structure of the data that is being transmitted between the client and server. Protobuf files define the message types and service interfaces that are used in the gRPC application.

### Message Types

Message types are defined using the `message` keyword in a protobuf file. Each message type contains one or more fields, which can be of various types (e.g., integers, strings, booleans, enums, nested messages).

Example protobuf message:

```protobuf
message Person {
  string name = 1;
  int32 age = 2;
  bool is_student = 3;
}
```

### Scalar Types

Protobuf supports a variety of scalar types, including:

- `int32`, `int64`, `uint32`, `uint64`, `sint32`, `sint64`: Signed and unsigned integers of 32 and 64 bits.
- `fixed32`, `fixed64`, `sfixed32`, `sfixed64`: Fixed-size integers of 32 and 64 bits.
- `float`, `double`: Floating-point numbers.
- `bool`: Boolean values.
- `string`: UTF-8 encoded strings.
- `bytes`: Arbitrary byte sequences.

### Enum Types

Enum types are defined using the `enum` keyword, and allow you to define a set of named constants.

Example protobuf enum:

```protobuf
enum Color {
  RED = 0;
  GREEN = 1;
  BLUE = 2;
}
```

### Nested Messages

Message types can contain nested message types, allowing you to create complex data structures.

Example nested message:

```protobuf
message Address {
  string street = 1;
  string city = 2;
  string state = 3;
  string zip = 4;
}

message Person {
  string name = 1;
  int32 age = 2;
  Address address = 3;
}
```

### Repeated Fields

Fields can be marked as `repeated`, allowing them to contain a sequence of values.

Example repeated field:

```protobuf
message Person {
  string name = 1;
  repeated string phone_numbers = 2;
}
```

## Service Definitions

In addition to defining message types, protobuf files also define the service interfaces that are used by the gRPC application. Service definitions are specified using the `service` keyword, and contain one or more RPC methods.

Example service definition:

```protobuf
service PersonService {
  rpc GetPerson(GetPersonRequest) returns (Person) {}
  rpc CreatePerson(CreatePersonRequest) returns (Person) {}
  rpc UpdatePerson(UpdatePersonRequest) returns (Person) {}
  rpc DeletePerson(DeletePersonRequest) returns (DeletePersonResponse) {}
}

message GetPersonRequest {
  string id = 1;
}

message CreatePersonRequest {
  string name = 1;
  int32 age = 2;
}

message UpdatePersonRequest {
  string id = 1;
  string name = 2;
  int32 age = 3;
}

message DeletePersonRequest {
  string id = 1;
}

message DeletePersonResponse {
  bool success = 1;
}

message Person {
  string id = 1;
  string name = 2;
  int32 age = 3;
}
```

In this example, the `PersonService` defines four RPC methods: `GetPerson`, `CreatePerson`, `UpdatePerson`, and `DeletePerson`. Each method takes a specific request message type and returns a response message type.

## Streaming

gRPC supports four different types of streaming:

1. **Unary**: A single request message and a single response message.
2. **Server Streaming**: A single request message and a stream of response messages.
3. **Client Streaming**: A stream of request messages and a single response message.
4. **Bidirectional Streaming**: A stream of request messages and a stream of response messages.

### Unary

In a unary RPC, the client sends a single request message and the server responds with a single response message.

Example unary RPC:

```protobuf
rpc GetPerson(GetPersonRequest) returns (Person) {}
```

### Server Streaming

In a server streaming RPC, the client sends a single request message and the server responds with a stream of response messages.

Example server streaming RPC:

```protobuf
rpc GetPersonHistory(GetPersonHistoryRequest) returns (stream PersonHistoryEvent) {}
```

### Client Streaming

In a client streaming RPC, the client sends a stream of request messages and the server responds with a single response message.

Example client streaming RPC:

```protobuf
rpc CreatePersonHistory(stream CreatePersonHistoryRequest) returns (CreatePersonHistoryResponse) {}
```

### Bidirectional Streaming

In a bidirectional streaming RPC, both the client and the server send a stream of messages to each other.

Example bidirectional streaming RPC:

```protobuf
rpc ChatStream(stream ChatMessage) returns (stream ChatMessage) {}
```

## Deadlines

Deadlines in gRPC are used to set a time limit for an RPC call to complete. If the RPC call does not complete within the specified deadline, the call is automatically canceled and an error is returned to the client.

Deadlines can be set at the client-side or the server-side, and can be used to implement timeouts, rate limiting, and other advanced functionality.

Example of setting a deadline on the client-side:

```python
from grpc import RpcError, StatusCode

try:
    response = stub.GetPerson(GetPersonRequest(), timeout=5)  # 5 second deadline
except RpcError as e:
    if e.code() == StatusCode.DEADLINE_EXCEEDED:
        print("RPC call timed out")
    else:
        print("RPC call failed with error:", e)
```

Example of setting a deadline on the server-side:

```python
from grpc import ServicerContext

def GetPerson(request, context: ServicerContext):
    # Check if the deadline has been exceeded
    if context.time_remaining() <= 0:
        context.abort(StatusCode.DEADLINE_EXCEEDED, "RPC call timed out")
    
    # Process the request and return the response
    return Person(...)
```

## Interceptors

gRPC interceptors are a powerful mechanism for injecting custom logic into the gRPC request and response lifecycle. Interceptors can be used for a variety of purposes, such as logging, authentication, rate limiting, and more.

There are two types of interceptors in gRPC:

1. **Server Interceptors**: Interceptors that are executed on the server-side, before and after the RPC method is executed.
2. **Client Interceptors**: Interceptors that are executed on the client-side, before and after the RPC call is made.

### Server Interceptors

Example of a simple server interceptor in Python:

```python
from grpc import ServerInterceptor, ServicerContext, Status, StatusCode

class LoggingInterceptor(ServerInterceptor):
    def intercept_service(self, continuation, handler_call_details):
        print(f"Received RPC call: {handler_call_details.method}")
        response = continuation(handler_call_details)
        print(f"Completed RPC call: {handler_call_details.method}")
        return response

server = grpc.server(
    futures.ThreadPoolExecutor(max_workers=10),
    interceptors=[LoggingInterceptor()])
```

In this example, the `LoggingInterceptor` class is a custom server interceptor that logs the incoming and outgoing RPC calls.

### Client Interceptors

Example of a simple client interceptor in Python:

```python
from grpc import ClientInterceptor, ClientCallDetails, invoke_unary_unary

class AuthInterceptor(ClientInterceptor):
    def __init__(self, api_key):
        self.api_key = api_key

    def intercept_unary_unary(self, continuation, client_call_details, request):
        # Add the API key to the request metadata
        metadata = (("x-api-key", self.api_key),)
        new_details = ClientCallDetails(
            client_call_details.method,
            client_call_details.timeout,
            metadata,
            client_call_details.credentials
        )
        return continuation(new_details, request)

stub = PersonServiceStub(channel)
interceptor = AuthInterceptor("my-api-key")
intercepted_stub = intercept_unary_unary(stub, interceptor)
response = intercepted_stub.GetPerson(GetPersonRequest(id="123"))
```

In this example, the `AuthInterceptor` class is a custom client interceptor that adds an API key to the request metadata before the RPC call is made.

## Architecture Diagram

Here is an architecture diagram illustrating the components and flow of a typical gRPC application:

```
+--------------+    +--------------+
|    Client    |    |    Server    |
+--------------+    +--------------+
       |                    |
       | gRPC RPC Call      | gRPC RPC Call
       |                    |
       v                    v
+--------------+    +--------------+
| Client Stub  |    | Server Stub  |
+--------------+    +--------------+
       |                    |
       | Protocol Buffers   | Protocol Buffers
       |                    |
       v                    v
+--------------+    +--------------+
|  Transport   |    |  Transport   |
|   (HTTP/2)   |    |   (HTTP/2)   |
+--------------+    +--------------+
       |                    |
       | TCP/IP             | TCP/IP
       |                    |
       v                    v
+--------------+    +--------------+
|     Network  |    |     Network  |
+--------------+    +--------------+
```

In this diagram, the client and server both use the gRPC protocol to communicate with each other. The client and server stubs handle the serialization and deserialization of the data using Protocol Buffers, and the transport layer (HTTP/2) handles the low-level networking details.

The client can use various types of streaming (unary, server, client, bidirectional) to interact with the server, and can also set deadlines for the RPC calls. Interceptors can be used on both the client and server side to add custom logic to the RPC call lifecycle.