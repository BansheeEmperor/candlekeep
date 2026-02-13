---
title: Linux Networking Configuration and Internals
description: Detailed technical documentation on Linux networking concepts, including the ip command, routing tables, network namespaces, bridges, and virtual ethernet (veth) pairs.
keywords: 
  - Linux
  - networking
  - ip command
  - routing table
  - network namespace
  - bridge
  - veth pair
category: networking
tags:
  - linux
  - networking
  - ip
  - routing
  - namespaces
  - bridge
  - veth
---

## The `ip` Command

The `ip` command is the primary tool for configuring and managing network interfaces, routing, and other network-related settings in Linux. It is a powerful and flexible command that provides a comprehensive set of features for network administration.

### Basic Usage

The basic syntax of the `ip` command is as follows:

```
ip [options] object [command [arguments]]
```

Where:

- `options` are optional flags that modify the behavior of the command
- `object` is the network entity you want to manage, such as `link`, `address`, `route`, `rule`, `neigh`, etc.
- `command` is the action you want to perform on the object, such as `add`, `delete`, `show`, etc.
- `arguments` are any additional parameters required by the command

Here are some common examples of using the `ip` command:

- `ip link show`: Display information about network interfaces
- `ip address add 192.168.1.100/24 dev eth0`: Add an IP address to the `eth0` interface
- `ip route add default via 192.168.1.1`: Add a default gateway route
- `ip neigh show`: Display the ARP cache (neighbor table)

### Advanced Usage

The `ip` command also supports more advanced functionality, such as:

- **Network namespaces**: You can use the `ip netns` subcommand to create, manage, and switch between network namespaces.
- **Routing tables**: The `ip route` subcommand allows you to view, add, and modify routing table entries.
- **Traffic control**: The `tc` command (part of the iproute2 package) provides advanced traffic control and shaping capabilities.
- **Tunneling**: The `ip tunnel` subcommand can be used to create and configure various types of network tunnels.

## Routing Tables

The routing table in Linux is a fundamental component of the network stack that determines how packets are forwarded between networks. The routing table consists of a set of rules that specify where traffic should be sent based on the destination IP address.

### Viewing the Routing Table

You can view the current routing table using the `ip route show` command:

```
$ ip route show
default via 192.168.1.1 dev eth0 proto dhcp metric 100
192.168.1.0/24 dev eth0 proto kernel scope link src 192.168.1.100
```

This output shows that:

1. The default gateway is `192.168.1.1`, and traffic for that destination is sent through the `eth0` interface.
2. Traffic destined for the `192.168.1.0/24` network is directly connected to the `eth0` interface.

### Modifying the Routing Table

You can add, delete, or modify routing table entries using the `ip route` subcommand. For example:

```
# Add a new route
ip route add 10.0.0.0/24 via 192.168.1.2 dev eth0

# Delete a route
ip route del 10.0.0.0/24

# Modify an existing route
ip route change 10.0.0.0/24 via 192.168.1.3 dev eth1
```

### Routing Tables and Network Namespaces

Each network namespace in Linux has its own independent routing table. You can view and manipulate the routing table for a specific namespace using the `ip netns exec` command:

```
# View the routing table in the "my-namespace" namespace
ip netns exec my-namespace ip route show

# Add a route in the "my-namespace" namespace
ip netns exec my-namespace ip route add 172.16.0.0/16 via 10.0.0.1
```

## Network Namespaces

Network namespaces in Linux are a powerful feature that allow you to create isolated network stacks within a single host. Each namespace has its own network interfaces, routing tables, firewall rules, and other network-related resources.

### Creating a Network Namespace

You can create a new network namespace using the `ip netns add` command:

```
ip netns add my-namespace
```

This will create a new namespace called `my-namespace`.

### Managing Network Interfaces in a Namespace

To view the network interfaces in a namespace, use the `ip netns exec` command:

```
ip netns exec my-namespace ip link show
```

You can also create and configure network interfaces within a namespace:

```
# Create a veth pair and assign one end to the namespace
ip link add veth0 type veth peer name veth1
ip link set veth1 netns my-namespace

# Configure the interface in the namespace
ip netns exec my-namespace ip address add 10.0.0.1/24 dev veth1
ip netns exec my-namespace ip link set veth1 up
```

This creates a virtual Ethernet (veth) pair, where one end (`veth0`) is in the default namespace, and the other end (`veth1`) is in the `my-namespace` namespace.

### Routing and Networking in Namespaces

Each network namespace has its own independent network stack, including routing tables, firewall rules, and network interfaces. You can use the `ip netns exec` command to perform network-related operations within a specific namespace:

```
# View the routing table in the "my-namespace" namespace
ip netns exec my-namespace ip route show

# Add a default route in the "my-namespace" namespace
ip netns exec my-namespace ip route add default via 10.0.0.2
```

Namespaces provide a way to create isolated network environments within a single host, which is useful for a variety of use cases, such as containerization, virtual machines, and network function virtualization (NFV).

## Bridges and Virtual Ethernet (veth) Pairs

Bridges and virtual Ethernet (veth) pairs are essential components for creating virtual network topologies in Linux.

### Bridges

A bridge is a network device that forwards traffic between different network segments based on the destination MAC address. Bridges operate at the data link layer (layer 2) of the network stack.

You can create a bridge using the `ip link add` command:

```
ip link add name br0 type bridge
```

This creates a new bridge device called `br0`. You can then attach network interfaces to the bridge using the `ip link set` command:

```
ip link set eth0 master br0
ip link set veth1 master br0
```

This adds the `eth0` and `veth1` interfaces to the `br0` bridge.

### Virtual Ethernet (veth) Pairs

A veth pair is a type of virtual network interface that consists of two linked interfaces. Traffic sent to one end of the pair is immediately received at the other end, providing a way to connect network namespaces or network devices.

You can create a veth pair using the `ip link add` command:

```
ip link add veth0 type veth peer name veth1
```

This creates two virtual network interfaces, `veth0` and `veth1`, which are linked together.

### Connecting Namespaces with veth Pairs

Veth pairs are commonly used to connect network namespaces, allowing communication between the isolated network stacks. Here's an example:

```
# Create a new namespace
ip netns add my-namespace

# Create a veth pair and attach one end to the namespace
ip link add veth0 type veth peer name veth1
ip link set veth1 netns my-namespace

# Configure the interfaces
ip address add 192.168.1.1/24 dev veth0
ip netns exec my-namespace ip address add 192.168.1.2/24 dev veth1
ip link set veth0 up
ip netns exec my-namespace ip link set veth1 up
```

In this example, we create a new network namespace called `my-namespace`, and then create a veth pair to connect it to the default network namespace. One end of the pair (`veth0`) is configured in the default namespace, while the other end (`veth1`) is configured in the `my-namespace` namespace.

This setup allows network traffic to flow between the two namespaces, enabling communication between the isolated network stacks.

## Advanced Topics

### Traffic Control and Shaping

The Linux kernel provides advanced traffic control and shaping capabilities through the `tc` command, which is part of the iproute2 package. With `tc`, you can create complex network policies, such as:

- Rate limiting
- Prioritization
- Packet queuing
- Congestion management
- Quality of Service (QoS) policies

Here's an example of using `tc` to add a simple rate-limiting policy:

```
# Create a qdisc (queuing discipline) to rate-limit egress traffic on eth0
tc qdisc add dev eth0 root tbf rate 10mbit burst 1000kb latency 50ms

# Remove the qdisc
tc qdisc del dev eth0 root
```

### IPtables and Firewalling

Linux uses the `iptables` command to configure the built-in netfilter firewall. You can use `iptables` to create firewall rules and policies, such as:

- Filtering incoming, outgoing, and forwarded traffic
- Network address translation (NAT)
- Port forwarding
- Connection tracking and state management

Here's an example of using `iptables` to block traffic to a specific IP address:

```
# Block traffic to 192.168.1.100
iptables -A INPUT -d 192.168.1.100 -j DROP
iptables -A OUTPUT -d 192.168.1.100 -j DROP

# List the current iptables rules
iptables -L
```

### Network Function Virtualization (NFV)

Network Function Virtualization (NFV) is a concept in which network functions, such as firewalls, load balancers, and routers, are virtualized and run as software on generic hardware. Linux, with its support for network namespaces, bridges, and veth pairs, is a popular platform for building NFV solutions.

In an NFV architecture, network functions are typically implemented as virtual network functions (VNFs) running in isolated network namespaces, with veth pairs and bridges used to interconnect the different components.

### Software-Defined Networking (SDN)

Software-Defined Networking (SDN) is a network architecture in which the control and data planes are decoupled, allowing the network control to become directly programmable and the underlying infrastructure to be abstracted from applications and network services.

Linux plays a crucial role in SDN implementations, providing the necessary building blocks, such as network namespaces, bridges, and the OpenFlow protocol support, to enable the creation of SDN controllers and virtual network switches.

## Conclusion

This technical documentation covers a wide range of Linux networking concepts, including the `ip` command, routing tables, network namespaces, bridges, and virtual Ethernet (veth) pairs. These fundamental components are essential for understanding and working with Linux networking, whether you're building virtual network topologies, implementing network function virtualization, or deploying software-defined networking solutions.

The information provided in this document should serve as a comprehensive reference for Linux network administrators and developers who need to dive deeper into the technical details of the Linux networking stack.