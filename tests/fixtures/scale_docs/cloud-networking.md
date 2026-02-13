---
title: Cloud Networking Concepts and Configurations
description: Comprehensive technical documentation on cloud networking, including VPC design, subnets, route tables, NAT gateways, VPC peering, Transit Gateway, and PrivateLink.
keywords: 
  - cloud networking
  - vpc
  - subnets
  - route tables
  - nat gateways
  - vpc peering
  - transit gateway
  - privatelink
category: cloud
tags:
  - aws
  - azure
  - gcp
  - networking
---

## VPC Design

A Virtual Private Cloud (VPC) is a virtual network within a cloud provider's data centers. It allows you to have full control over the network environment, including IP address ranges, subnets, route tables, and gateways.

### IP Address Ranges

When creating a VPC, you must specify the IP address range for the VPC in the form of a Classless Inter-Domain Routing (CIDR) block. This is typically a private IP address range, such as `10.0.0.0/16`, `172.16.0.0/12`, or `192.168.0.0/16`.

Example VPC configuration:

```
resource "aws_vpc" "example" {
  cidr_block = "10.0.0.0/16"
}
```

### Subnets

Within a VPC, you can create one or more subnets. Subnets are a division of the VPC's IP address range, and they allow you to segment your network for better organization and control.

Each subnet must have a CIDR block that is a subset of the VPC's CIDR block. For example, if the VPC CIDR is `10.0.0.0/16`, you could create two subnets with the following CIDR blocks:

- Subnet 1: `10.0.0.0/24`
- Subnet 2: `10.0.1.0/24`

Example subnet configuration:

```
resource "aws_subnet" "public_1" {
  vpc_id     = aws_vpc.example.id
  cidr_block = "10.0.0.0/24"
  availability_zone = "us-west-2a"
}

resource "aws_subnet" "private_1" {
  vpc_id     = aws_vpc.example.id
  cidr_block = "10.0.1.0/24"
  availability_zone = "us-west-2b"
}
```

### Route Tables

Route tables are used to control the routing of traffic within a VPC and to the internet or other networks. Each subnet in a VPC is associated with a route table, which determines where network traffic from that subnet is directed.

The default route table in a VPC has a route that allows all traffic within the VPC CIDR block to be routed directly. You can also create custom route tables and associate them with specific subnets.

Example route table configuration:

```
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.example.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.example.id
  }
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.example.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_nat_gateway.example.id
  }
}
```

### Internet Gateways

An Internet Gateway is a network component that allows communication between resources in a VPC and the internet. It is attached to a VPC and enables outbound internet access for resources in public subnets.

Example Internet Gateway configuration:

```
resource "aws_internet_gateway" "example" {
  vpc_id = aws_vpc.example.id
}
```

### NAT Gateways

A NAT (Network Address Translation) Gateway is a managed service that provides outbound internet access for resources in private subnets. It allows instances in private subnets to connect to the internet or other AWS services, while preventing the internet from initiating a connection to those instances.

Example NAT Gateway configuration:

```
resource "aws_nat_gateway" "example" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public_1.id
}

resource "aws_eip" "nat" {
  vpc   = true
  dependency_on = [aws_internet_gateway.example]
}
```

### VPC Peering

VPC peering is a networking connection between two VPCs that enables you to route traffic between them using private IP addresses. This allows resources in one VPC to communicate with resources in the other VPC as if they were in the same network.

Example VPC Peering configuration:

```
resource "aws_vpc_peering_connection" "example" {
  peer_vpc_id = aws_vpc.other.id
  vpc_id      = aws_vpc.example.id
  region      = "us-west-2"
}

resource "aws_route_table_association" "public_1" {
  subnet_id      = aws_subnet.public_1.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route" "public_to_peer" {
  route_table_id            = aws_route_table.public.id
  destination_cidr_block    = aws_vpc.other.cidr_block
  vpc_peering_connection_id = aws_vpc_peering_connection.example.id
}
```

## Transit Gateway

AWS Transit Gateway is a service that makes it easier to connect VPCs and on-premises networks to a central hub. It acts as a router, allowing you to connect multiple VPCs and on-premises networks to a single Transit Gateway, simplifying your network architecture and reducing the number of peering connections required.

Example Transit Gateway configuration:

```
resource "aws_ec2_transit_gateway" "example" {
  description = "Example Transit Gateway"
}

resource "aws_ec2_transit_gateway_vpc_attachment" "example" {
  subnet_ids         = [aws_subnet.private_1.id, aws_subnet.private_2.id]
  transit_gateway_id = aws_ec2_transit_gateway.example.id
  vpc_id             = aws_vpc.example.id
}

resource "aws_route" "private_to_tgw" {
  route_table_id         = aws_route_table.private.id
  destination_cidr_block = "0.0.0.0/0"
  transit_gateway_id     = aws_ec2_transit_gateway.example.id
}
```

## PrivateLink

AWS PrivateLink is a VPC-based service that enables private connectivity between VPCs, services, and on-premises applications. It provides a secure and scalable way to access services hosted on AWS or on-premises, without exposing the service to the public internet.

PrivateLink uses Network Load Balancers and Elastic Network Interfaces to enable private communication between the service consumer and the service provider.

Example PrivateLink configuration:

```
# Service Provider Configuration
resource "aws_lb" "example_service" {
  internal = true
  load_balancer_type = "network"
  subnet_mapping {
    subnet_id = aws_subnet.private_1.id
  }
}

resource "aws_vpc_endpoint_service" "example" {
  acceptance_required        = false
  network_load_balancer_arns = [aws_lb.example_service.arn]
}

# Service Consumer Configuration
resource "aws_vpc_endpoint" "example" {
  vpc_id              = aws_vpc.example.id
  service_name        = aws_vpc_endpoint_service.example.service_name
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  subnet_ids          = [aws_subnet.private_1.id, aws_subnet.private_2.id]
  security_group_ids   = [aws_security_group.private_endpoint.id]
}
```

In this example, the service provider creates a Network Load Balancer and a VPC Endpoint Service, while the service consumer creates a VPC Endpoint to access the service privately.

## Conclusion

This comprehensive technical documentation covers the key concepts and configurations related to cloud networking, including VPC design, subnets, route tables, NAT gateways, VPC peering, Transit Gateway, and PrivateLink. By understanding these topics in depth, you can design and implement robust and secure cloud networking architectures to meet your application's requirements.