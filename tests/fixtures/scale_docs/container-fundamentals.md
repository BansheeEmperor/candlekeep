---
title: Container Fundamentals and Docker
description: A comprehensive technical guide to the core concepts and components that power modern container technologies, with a focus on Docker.
keywords: 
  - containers
  - docker
  - namespaces
  - cgroups
  - overlay filesystems
  - image layers
  - multi-stage builds
category: DevOps
tags:
  - containers
  - docker
  - linux
  - virtualization
  - microservices
---

## Container Fundamentals

Containers are a method of operating system virtualization that allow applications and their dependencies to be packaged into isolated, portable units called containers. Containers share the host operating system's kernel, but are isolated from each other and the host system.

The key components that enable container technology are:

### Namespaces
Namespaces are a Linux kernel feature that provide isolation between processes. Different types of namespaces exist to isolate various aspects of a process' environment, including:

- **Mount namespaces**: Isolate the filesystem mounts visible to a process
- **PID namespaces**: Isolate process IDs, so processes in different namespaces can have the same PID
- **Network namespaces**: Isolate network interfaces, routing tables, and iptables rules
- **UTS namespaces**: Isolate hostname and domain name
- **IPC namespaces**: Isolate inter-process communication resources

Processes running in different namespaces are isolated from each other, creating the illusion of running on a dedicated system.

### Control Groups (cgroups)
Control groups are a Linux kernel feature that allow resources like CPU, memory, disk I/O, and network to be hierarchically partitioned and isolated for a collection of processes. This provides resource management and enforcement capabilities for containers.

Cgroups allow you to:
- Limit the amount of resources (CPU, memory, disk, network, etc.) a container can use
- Prioritize resources between containers
- Account for resource usage
- Deny or freeze access to resources

### Union File Systems (OverlayFS)
Union file systems allow multiple file directories to be transparently overlaid, forming a single unified file system. This is the foundation for building image layers in container technologies like Docker.

OverlayFS is a popular union file system implementation used in many container runtimes. It allows multiple read-only "lower" directories to be combined with a single read-write "upper" directory, forming a merged view.

The key benefit of union file systems is their ability to create lightweight, incremental changes to a base file system, which is crucial for building and distributing container images efficiently.

## Docker

[Docker](https://www.docker.com/) is the most widely adopted container platform, providing a complete ecosystem for building, distributing, and running containerized applications. Docker utilizes the core Linux container primitives (namespaces, cgroups, OverlayFS) to provide a user-friendly experience for developers and operators.

### Docker Architecture
The Docker architecture consists of the following main components:

1. **Docker Client**: The command-line interface (CLI) used to interact with the Docker daemon.
2. **Docker Daemon**: The background process that manages Docker objects like images, containers, networks, and volumes.
3. **Docker Registry**: A storage and content delivery system, holding Docker images. The public Docker Hub registry is the default, but you can also run a private registry.
4. **Docker Objects**:
   - **Images**: Lightweight, standalone, executable package of software that includes everything needed to run an application: code, runtime, system tools, system libraries, and settings.
   - **Containers**: A runnable instance of a Docker image. Containers are isolated and secure application platforms.
   - **Networks**: Allows containers to communicate with each other and the outside world.
   - **Volumes**: Provides a data storage mechanism for containers.

### Building Docker Images
Docker images are built using a `Dockerfile`, a text-based script that contains all the instructions to assemble a Docker image. Here's an example `Dockerfile`:

```dockerfile
FROM node:14-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
EXPOSE 3000
CMD ["npm", "start"]
```

This `Dockerfile` starts with the `node:14-alpine` base image, sets the working directory to `/app`, copies the `package.json` and `package-lock.json` files, installs dependencies, copies the application code, exposes port 3000, and sets the startup command to `npm start`.

To build the image, run:

```
docker build -t my-app .
```

This will create a new Docker image tagged as `my-app`.

### Running Docker Containers
Once you have a Docker image, you can run it as a container:

```
docker run -p 8080:3000 --name my-container my-app
```

This command runs the `my-app` image as a container named `my-container`, mapping port 8080 on the host to port 3000 inside the container.

### Docker Layers and Image Optimization
Docker images are built in layers, where each instruction in the `Dockerfile` creates a new layer. This layered approach provides several benefits:

- **Caching**: Docker caches each layer, speeding up subsequent builds if the layer hasn't changed.
- **Reusability**: Layers can be shared between images, reducing image size.
- **Efficient Distribution**: Only the changed layers need to be transferred when pushing/pulling images.

To optimize Docker image size, you can leverage techniques like:

- Using a smaller base image (e.g., `alpine` instead of `ubuntu`)
- Combining multiple `RUN` commands with `&&` to reduce the number of layers
- Utilizing multi-stage builds to minimize the final image size

### Multi-stage Builds
Multi-stage builds allow you to use multiple `FROM` statements in a single `Dockerfile`, each with its own build environment. This is particularly useful for compiling applications with complex build dependencies, while still producing a small, optimized final image.

Here's an example of a multi-stage `Dockerfile` for a Go application:

```dockerfile
# Build stage
FROM golang:1.16-alpine AS build
WORKDIR /src
COPY . .
RUN go build -o myapp .

# Runtime stage
FROM alpine:latest
WORKDIR /app
COPY --from=build /src/myapp .
CMD ["./myapp"]
```

In this example, the first `FROM` statement creates a build environment with the Go compiler, while the second `FROM` statement creates a lightweight runtime environment based on `alpine:latest` and copies the compiled binary from the first stage.

### Docker Networking
Docker provides several networking modes to connect containers:

- **Bridge**: The default network mode, where containers are connected to a virtual bridge network and can communicate with each other.
- **Host**: Containers share the host's network stack, allowing direct access to host network interfaces.
- **None**: Containers are not connected to any network, and have only the loopback interface.
- **Overlay**: Allows containers in different Docker daemons to communicate, forming a distributed network.

You can also create custom Docker networks and configure DNS, load balancing, and other network-related features.

### Docker Volumes
Docker volumes provide a way to persist data generated by and used by Docker containers. There are several volume types:

- **Host Volumes**: Data is stored on the Docker host's filesystem.
- **Named Volumes**: Docker manages the volume's lifecycle and storage location.
- **Anonymous Volumes**: Temporary volumes that are deleted when the container is removed.

Volumes can be mounted into containers to provide persistent storage or share data between containers.

### Docker Compose
Docker Compose is a tool for defining and running multi-container Docker applications. It uses a YAML file to configure the application's services, networks, and volumes. This simplifies the process of building, starting, and managing complex, multi-container applications.

Here's an example `docker-compose.yml` file:

```yaml
version: '3'
services:
  web:
    build: .
    ports:
      - "8080:80"
    depends_on:
      - db
  db:
    image: postgres:12
    volumes:
      - db-data:/var/lib/postgresql/data
volumes:
  db-data:
```

This configuration defines two services: `web` and `db`. The `web` service builds an image from the current directory and exposes port 8080. The `db` service uses the official PostgreSQL 12 image and persists data in a named volume `db-data`.

## Linux Namespaces

Linux namespaces are a fundamental building block of container technology, providing isolation between processes. There are several types of namespaces:

### Mount Namespaces
Mount namespaces isolate the filesystem mounts visible to a process and its child processes. This allows containers to have their own view of the filesystem, independent of the host system.

You can create a new mount namespace using the `unshare` command:

```
unshare --mount /bin/sh
```

This will start a new shell process in a separate mount namespace, where any filesystem mounts performed will be isolated from the host system.

### PID Namespaces
PID namespaces isolate process IDs, allowing each container to have its own set of process IDs starting from 1 (the init process). This ensures that processes in different containers do not conflict with each other.

You can create a new PID namespace using the `unshare` command:

```
unshare --pid /bin/sh
```

Now, running `ps` in this new namespace will only show processes within the namespace.

### Network Namespaces
Network namespaces provide isolated network stacks, including network interfaces, routing tables, and iptables rules. This allows each container to have its own network configuration, such as IP addresses, routes, and firewall rules.

You can create a new network namespace using the `ip` command:

```
ip netns add mynetns
ip netns exec mynetns /bin/sh
```

This creates a new network namespace named `mynetns` and starts a new shell process within it.

### Other Namespaces
There are also other types of namespaces, such as:

- **UTS Namespaces**: Isolate hostname and domain name
- **IPC Namespaces**: Isolate inter-process communication resources
- **User Namespaces**: Isolate user and group IDs

These namespaces provide different levels of isolation for container environments.

## Control Groups (cgroups)

Control groups (cgroups) are a Linux kernel feature that allow resources like CPU, memory, disk I/O, and network to be hierarchically partitioned and isolated for a collection of processes. Cgroups provide resource management and enforcement capabilities for containers.

### Cgroup Hierarchy
Cgroups are organized in a hierarchical manner, similar to a filesystem. Each cgroup can have child cgroups, allowing for fine-grained resource allocation and control.

The root cgroup `/` is the parent of all other cgroups. You can create new cgroups under the root cgroup using the `mkdir` command:

```
mkdir /sys/fs/cgroup/cpu/my-cgroup
```

This creates a new CPU cgroup named `my-cgroup` under the root cgroup.

### Cgroup Controllers
Cgroup controllers are responsible for managing and enforcing resource limits for a specific resource type, such as CPU, memory, or disk I/O. Some common cgroup controllers include:

- **cpu**: Allows setting CPU shares, CPU quotas, and CPU period
- **memory**: Allows setting memory limits and swapping
- **blkio**: Allows setting read/write bandwidth limits for block devices
- **network**: Allows setting network bandwidth limits

You can enable or disable specific controllers for a cgroup using the `cgroup.subtree_control` file.

### Cgroup Configuration
You can configure resource limits for a cgroup by writing values to the corresponding controller files. For example, to set a CPU limit for the `my-cgroup` cgroup:

```
echo "100000" > /sys/fs/cgroup/cpu/my-cgroup/cpu.cfs_quota_us
echo "100000" > /sys/fs/cgroup/cpu/my-cgroup/cpu.cfs_period_us
```

This sets a CPU quota of 100% for the `my-cgroup` cgroup.

### Cgroups in Containers
Container runtimes like Docker and Kubernetes use cgroups to manage and enforce resource limits for containers. When you run a container, the runtime automatically creates a new cgroup for that container and applies the specified resource limits.

You can view the cgroups associated with a running container using the `docker inspect` or `kubectl describe` commands.

## Union File Systems (OverlayFS)

Union file systems, such as OverlayFS, allow multiple file directories to be transparently overlaid, forming a single unified file system. This is a fundamental building block for container image layers.

### OverlayFS Architecture
OverlayFS consists of the following components:

- **Lower Directory**: One or more read-only "lower" directories that form the base file system.
- **Upper Directory**: A single read-write "upper" directory that contains the modifications.
- **Merged Directory**: The unified view of the lower and upper directories.

When a file or directory is accessed, OverlayFS first checks the upper directory, and if the file is not found, it checks the lower directory. This allows new files to be added, and existing files to be modified or removed, without affecting the lower directory.

Here's an example OverlayFS mount:

```
mount -t overlay overlay -o lowerdir=/lower,upperdir=/upper,workdir=/work /merged
```

This mounts an OverlayFS file system with `/lower` as the lower directory, `/upper` as the upper directory, `/work` as the working directory, and `/merged` as the merged view.

### OverlayFS in Containers
OverlayFS is widely used in container runtimes, such as Docker and Kubernetes, to build and manage container image layers. Each layer in a container image is represented as a directory in the OverlayFS, with the base layer as the lower directory and subsequent layers as upper directories.

When a container is started, the container runtime mounts the OverlayFS with the appropriate image layers, providing the container with a unified view of the file system.

This layered approach allows for efficient storage and distribution of container images, as only the changed layers need to be transferred when pushing or pulling images.

## Image Layers and Multi-stage Builds

### Image Layers
Docker images are built in layers, where each instruction in the `Dockerfile` creates a new layer. This layered approach provides several benefits:

- **Caching**: Docker caches each layer, speeding up subsequent builds if the layer hasn't changed.
- **Reusability**: Layers can be shared between images, reducing image size.
- **Efficient Distribution**: Only the changed layers need to be transferred when pushing/pulling images.

Each layer is represented as a directory in the OverlayFS, with the base layer as the lower directory and subsequent layers as upper directories.

### Multi-stage Builds
Multi-stage builds allow you to use multiple `FROM` statements in a single `Dockerfile`, each with its own build environment. This is particularly useful for compiling applications with complex build dependencies, while still producing a small, optimized final image.

Here's an example of a multi-stage `Dockerfile` for a Go application:

```dockerfile
# Build stage
FROM golang:1.16-alpine AS build
WORKDIR /src
COPY . .
RUN go build -o myapp .

# Runtime stage
FROM alpine:latest
WORKDIR /app
COPY --from=build /src/myapp .
CMD ["./myapp"]
```

In this example, the first `FROM` statement creates a build environment with the Go compiler, while the second `FROM` statement creates a lightweight runtime environment based on `alpine:latest` and copies the compiled binary from the first stage.

The `--from=build` argument in the `COPY` instruction refers to the build stage, allowing you to selectively copy artifacts from previous stages into the final image.

Multi-stage builds help you achieve the following benefits:

- **Reduced Image Size**: The final image only contains the runtime dependencies, not the build tools.
- **Improved Security**: The runtime image has a smaller attack surface.
- **Maintainable Dockerfiles**: Separating build and runtime environments makes the `Dockerfile` more modular and easier to understand.

By leveraging multi-stage builds, you can create optimized, lean container images that are efficient to build, distribute, and run.