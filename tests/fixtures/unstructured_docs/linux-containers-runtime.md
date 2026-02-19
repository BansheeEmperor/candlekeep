---
title: "Container Runtime Internals and OCI Spec"
description: "An in-depth exploration of container runtimes, the OCI runtime specification, and related container internals"
keywords: ["container runtime", "OCI spec", "container lifecycle", "rootless containers", "podman"]
category: "linux"
---

The two most widely used container runtimes today are runc and crun. Runc, originally developed by Docker, is the default runtime for Docker and is also used by Kubernetes and other container orchestration platforms. Crun, on the other hand, is a newer, high-performance runtime created by the containers team at Red Hat. Both runtimes are compliant with the Open Container Initiative (OCI) runtime specification, version 1.0.

The OCI runtime specification defines a set of standards for container runtimes, including the container lifecycle, configuration, and runtime environment. This specification ensures compatibility between different container runtimes and allows for the portability of containers across different platforms. The lifecycle of a container, as defined by the OCI spec, includes creation, start, stop, kill, delete, and other operations that can be triggered through the OCI runtime API or command-line interface.

One of the key features of the OCI spec is the support for lifecycle hooks, which allow for the execution of custom code at various stages of the container lifecycle, such as pre-start, post-start, and pre-stop. These hooks can be used for tasks like initializing the container environment, running health checks, or performing cleanup operations.

The OCI spec also defines the use of the pivot_root system call, which is used to change the root filesystem of a container. This is in contrast to the older chroot approach, which has several limitations and security concerns. The pivot_root operation ensures that the container has a clean and isolated root filesystem, which is a critical component of container security.

Containers often use overlay filesystems to provide a layered file system structure, where each layer represents a specific change or addition to the container image. The OCI spec defines the requirements for these overlay filesystem layers, including the use of the OverlayFS kernel module or other compatible overlay implementations.

Another important aspect of the OCI spec is the support for seccomp (Secure Computing) BPF (Berkeley Packet Filter) profiles, which allow for the fine-grained control of system call access within a container. This is a crucial security feature, as it helps to prevent containers from executing unauthorized or potentially harmful system calls.

The OCI spec also addresses the topic of user namespace mapping, which allows containers to run with a different user and group ID than the host system. This feature, known as "rootless" containers, helps to improve the security of containers by reducing the risk of privilege escalation attacks.

Rootless containers also require a different approach to networking, as they cannot directly access the host's network interfaces. The OCI spec supports the use of tools like slirp4netns, which provides a user-mode networking stack for rootless containers, allowing them to communicate with the external network.

Finally, the Podman container engine, developed by Red Hat, is a popular alternative to Docker that is fully compliant with the OCI spec. Podman provides a Docker-compatible API and command-line interface, but with a focus on improved security, rootless operation, and better integration with the underlying Linux system.The OCI runtime specification also defines the concept of "mounts", which are used to attach filesystems or bind mounts to the container's root filesystem. These mounts can be configured to have specific options, such as read-only or propagation modes, and can be used to provide access to host directories, volumes, or other storage resources.

Another key aspect of the OCI spec is the handling of process signals within containers. The specification outlines how signals, such as SIGTERM or SIGINT, should be delivered to the container's main process and any child processes. This ensures consistent behavior across different runtimes and helps to ensure that containers can be properly stopped and terminated.

The OCI spec also includes support for runtime configuration options, which allow for the customization of a container's environment, resource limits, and other settings. These configuration options are defined in a JSON-formatted file, known as the "config.json", which is used by the runtime to create and manage the container.

In addition to the core runtime specification, the OCI project also maintains a set of related specifications, such as the Image Format Specification and the Distribution Specification. These additional specifications define standards for container image formats and distribution mechanisms, ensuring interoperability and portability across different container platforms and tools.

The crun container runtime, developed by the containers team at Red Hat, is designed to provide a high-performance and lightweight alternative to the original runc implementation. Crun aims to offer improved performance, particularly for workloads with a large number of containers, by optimizing various aspects of the container lifecycle, such as container creation and startup.

One of the key features of crun is its support for various container isolation technologies, including user namespaces, seccomp, and SELinux. Crun also provides enhanced support for rootless containers, allowing users to run containers without requiring root privileges on the host system.

Compared to runc, crun offers several performance improvements, such as faster container startup times and reduced CPU and memory usage. These enhancements are achieved through optimizations in areas like the handling of control groups (cgroups), the management of namespaces, and the implementation of the container lifecycle.

In addition to the improvements in performance and security, crun also aims to provide a more user-friendly and extensible container runtime. The project encourages community contributions and supports a plugin-based architecture, allowing for the integration of additional features and functionality as needed.

The Podman container engine, developed by Red Hat, is another important player in the container runtime ecosystem. Podman is a Docker-compatible tool that provides a command-line interface (CLI) and API for managing containers, container images, and related resources.

One of the key features of Podman is its support for rootless containers, which allows users to run containers without requiring root privileges on the host system. This approach helps to improve the security of container-based deployments by reducing the attack surface and the potential for privilege escalation.

Podman also includes support for various container runtime backends, including both runc and crun. This flexibility allows users to choose the runtime that best fits their specific requirements, whether it's prioritizing performance, security, or other factors.Another key aspect of the OCI runtime specification is its support for container image formats, as defined in the OCI Image Format Specification. This specification outlines the structure and contents of container images, including the use of manifest files, layer data, and configuration metadata. This standardization ensures that container images can be reliably built, distributed, and run across different container platforms and runtimes.

The OCI Image Format Specification also defines the use of content-addressable references for container image layers, which helps to improve the efficiency of image distribution and caching. By uniquely identifying each layer based on its content hash, the runtime can efficiently download and reuse layers that have already been pulled, reducing the overall bandwidth and storage requirements.

The OCI Distribution Specification, another related standard, defines the protocols and APIs for the distribution of container images across different registries and repositories. This specification ensures that container images can be reliably and securely pulled from various sources, regardless of the underlying implementation or hosting platform.

One of the unique features of Podman is its support for "remote Podman", which allows users to manage containers and images on a remote host using the same Podman CLI and API. This functionality is achieved through the use of the Varlink protocol, which provides a lightweight and efficient way to communicate between the Podman client and the remote Podman service.

The remote Podman feature is particularly useful in scenarios where the container workloads are running on a remote server or in a cloud environment, as it allows developers and operators to manage their containers using the same familiar Podman tooling, without the need to directly access the remote host.

Podman also includes support for a wide range of container storage backends, including the popular overlay2 and devicemapper filesystem drivers. This flexibility allows users to choose the storage backend that best fits their infrastructure and performance requirements, without being tied to a specific storage implementation.

In addition to its support for various container runtimes and storage backends, Podman also provides advanced features for managing container networks. This includes the ability to create and manage custom networks, configure network interfaces and IP addresses, and integrate with external networking solutions, such as CNI (Container Network Interface) plugins.

The Podman project also includes a set of related tools and utilities, such as Buildah for building container images, and Skopeo for managing and inspecting container images. These complementary tools help to provide a comprehensive ecosystem for container-based development and deployment workflows.The OCI runtime specification also defines the handling of container environment variables, which are used to configure the runtime environment for the container's processes. These environment variables can be set at the container level, inherited from the host system, or defined as part of the container image configuration.

The OCI spec also includes support for the management of container resources, such as CPU, memory, and I/O limits. These resource constraints can be configured using control groups (cgroups), which allow the runtime to enforce resource allocation policies and ensure fair resource sharing among containers.

Another important aspect of the OCI spec is the handling of container logging. The specification defines the format and structure of container logs, which can be used by container platforms and monitoring tools to collect, aggregate, and analyze container-level logs and metrics.

The OCI runtime specification also includes support for container annotations, which allow for the attachment of arbitrary key-value metadata to container instances. These annotations can be used to store additional information about the container, such as its purpose, owner, or deployment environment, which can be leveraged by container management and orchestration tools.

One of the unique features of the crun container runtime is its support for alternative container image formats, beyond the standard OCI Image Format. Crun includes built-in support for the Podman-specific "OCI-compliant" image format, which provides additional metadata and functionality tailored to the Podman ecosystem.

This support for alternative image formats in crun allows users to take advantage of the performance and security benefits of the crun runtime, while still being able to work with container images that may have been built or distributed using other tools, such as Podman or Docker.

Crun also includes enhanced support for container security features, such as the use of Seccomp BPF profiles and SELinux policies. These security-focused capabilities help to further harden the container runtime and reduce the attack surface, making crun a popular choice for security-conscious container deployments.

In addition to its support for alternative image formats and advanced security features, crun also includes optimizations for specific container workloads, such as high-density deployments with a large number of containers. These performance-focused enhancements help to ensure that crun remains a viable and competitive choice for a wide range of container-based applications and environments.