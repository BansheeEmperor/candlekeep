---
title: AWS Well-Architected Framework Pillars
description: Detailed technical documentation on the six pillars of the AWS Well-Architected Framework.
keywords:
  - aws
  - well-architected
  - operational excellence
  - security
  - reliability
  - performance
  - cost optimization
  - sustainability
category: cloud architecture
tags:
  - aws
  - well-architected
  - design principles
  - operational excellence
  - security
  - reliability
  - performance
  - cost optimization
  - sustainability
---

## Operational Excellence

The Operational Excellence pillar includes the ability to run and monitor systems to deliver business value, and to continually improve supporting processes and procedures.

### Design Principles

The key design principles for Operational Excellence in the AWS Well-Architected Framework are:

1. **Perform operations as code**: Automate the execution of your operational procedures and the deployment of your applications.
2. **Annotate documentation**: Embed operational documentation directly into your technology so it is always available and up-to-date.
3. **Make frequent, small, reversible changes**: Design systems to allow for incremental updates. Break large, complex changes into smaller steps that can be reversed if needed.
4. **Refine operations procedures frequently**: As you evolve your systems and as business needs change, frequently review and improve your operational procedures.
5. **Anticipate failure**: Expect failures and have processes in place to respond and recover quickly.
6. **Learn from all operational events**: Learn from both successful and unsuccessful operational events. Share what is learned across your organization.

### Key Areas

The key areas of Operational Excellence in the AWS Well-Architected Framework are:

#### Operations
- Implement strong change management processes
- Ensure operational procedures are well-documented and easy to execute
- Monitor systems proactively and set appropriate alerts
- Maintain observability through logging, metrics, and tracing

#### Incident Response
- Have effective incident response and escalation processes
- Leverage automated remediation where possible
- Conduct post-incident analysis and update procedures accordingly

#### Continuous Improvement
- Regularly review operational performance metrics
- Continuously improve your procedures based on operational data
- Foster a culture of operational excellence

### Example
Here is an example of how to implement Operational Excellence using AWS services:

1. **Operations**:
   - Use AWS Config to track infrastructure changes and detect drift
   - Leverage AWS CloudFormation to define infrastructure as code and automate deployments
   - Configure Amazon CloudWatch to monitor key metrics and set alarms
   - Implement AWS Systems Manager to manage and automate operational tasks
   - Use AWS CloudTrail to audit actions taken in your AWS environment

2. **Incident Response**:
   - Establish Amazon SNS topics to notify on-call teams of critical events
   - Leverage Amazon EventBridge to automatically trigger remediation actions
   - Implement AWS Lambda functions to execute automated runbooks
   - Use AWS Chatbot to enable interactive incident management through Slack or other chat tools

3. **Continuous Improvement**:
   - Analyze CloudWatch Logs and AWS X-Ray traces to identify operational issues
   - Conduct regular operational reviews and document lessons learned
   - Continuously update CloudFormation templates and runbooks based on feedback
   - Share best practices and learnings across teams using AWS Organizations and Control Tower

By following these design principles and leveraging the appropriate AWS services, you can achieve a high degree of Operational Excellence in your cloud-based systems.

## Security

The Security pillar includes the ability to protect data, systems, and assets to take advantage of cloud technologies to improve your security.

### Design Principles

The key design principles for Security in the AWS Well-Architected Framework are:

1. **Implement a strong identity foundation**: Centralize identity management, and use it across multiple accounts and applications.
2. **Enable traceability**: Monitor, alert, and audit actions and changes to your environment in real time.
3. **Apply security at all layers**: Apply a defense in-depth approach with multiple security controls.
4. **Automate security best practices**: Reduce human error and enable rapid response times with automated deployment and configuration.
5. **Protect data in transit and at rest**: Classify your data into sensitivity levels and use appropriate controls to protect it.
6. **Keep people away from data**: Use mechanisms and tools to reduce or eliminate the need for direct access or manual processing of data.
7. **Prepare for security events**: Determine potential security events and create response plans.

### Key Areas

The key areas of Security in the AWS Well-Architected Framework are:

#### Identity and Access Management
- Implement centralized identity management using AWS IAM
- Use multi-factor authentication (MFA) to secure access
- Leverage AWS Organizations and Service Control Policies for account management

#### Detective Controls
- Enable AWS CloudTrail to track API calls and account activity
- Configure Amazon GuardDuty for continuous threat detection
- Utilize Amazon Macie to discover and protect sensitive data

#### Infrastructure Protection
- Use AWS Shield to protect against DDoS attacks
- Leverage AWS WAF to filter malicious web traffic
- Implement AWS VPC and security groups for network isolation

#### Data Protection
- Encrypt data at rest using AWS KMS and EBS encryption
- Protect data in transit with SSL/TLS and AWS PrivateLink
- Classify and manage your data using AWS Macie and AWS Data Pipeline

#### Incident Response
- Establish an incident response plan and test it regularly
- Automate response actions using AWS Lambda and Amazon SNS
- Capture logs and metrics for forensic analysis with AWS CloudWatch

### Example
Here is an example of how to implement Security best practices using AWS services:

1. **Identity and Access Management**:
   - Create an AWS Organizations root account and enable consolidated billing
   - Define IAM users, roles, and policies to control access to resources
   - Enable multi-factor authentication (MFA) for all IAM users
   - Leverage AWS Single Sign-On (AWS SSO) for federated access

2. **Detective Controls**:
   - Enable AWS CloudTrail to log all API calls across your AWS accounts
   - Configure Amazon GuardDuty to continuously monitor for threats
   - Set up Amazon Macie to discover and classify sensitive data

3. **Infrastructure Protection**:
   - Create VPCs with appropriate subnets, route tables, and security groups
   - Implement AWS Shield to protect against DDoS attacks
   - Configure AWS WAF web ACLs to filter malicious web requests

4. **Data Protection**:
   - Use AWS KMS to create and manage encryption keys for your data at rest
   - Leverage AWS PrivateLink to enable private connectivity to services
   - Classify your data using Amazon Macie and apply appropriate controls

5. **Incident Response**:
   - Document your incident response plan and conduct regular testing
   - Use Amazon SNS to notify on-call teams of security events
   - Leverage AWS Lambda to automate remediation actions
   - Analyze CloudWatch Logs and CloudTrail events for forensic purposes

By following these design principles and leveraging the appropriate AWS services, you can achieve a high degree of Security in your cloud-based systems.

## Reliability

The Reliability pillar includes the ability of a system to recover from infrastructure or service disruptions, dynamically acquire computing resources to meet demand, and mitigate disruptions such as misconfigurations or transient network issues.

### Design Principles

The key design principles for Reliability in the AWS Well-Architected Framework are:

1. **Automatically recover from failure**: Anticipate and address failures before they occur.
2. **Test recovery procedures**: Use automation to simulate different failure scenarios and validate procedures.
3. **Scale horizontally to increase aggregate system availability**: Add or remove resources dynamically based on demand.
4. **Stop guessing capacity**: Implement solutions to automatically scale up or down based on actual usage.
5. **Manage change in automation**: Use codified change management processes to make system changes reliably.
6. **Improve over time**: Regularly review the system for opportunities to increase reliability.

### Key Areas

The key areas of Reliability in the AWS Well-Architected Framework are:

#### Foundations
- Ensure you have a well-designed and tested network topology
- Leverage AWS Auto Scaling to handle changes in demand
- Implement AWS CloudFormation to manage infrastructure as code

#### Change Management
- Use AWS CodePipeline and AWS CodeDeploy for application deployments
- Leverage blue/green or canary deployment strategies
- Implement rollback mechanisms to quickly revert changes

#### Failure Management
- Design your system to be fault-tolerant and able to recover from failures
- Leverage AWS services like Amazon SQS, Amazon SNS, and AWS Lambda for decoupling
- Implement circuit breakers and retry logic to handle transient failures

#### Scaling
- Use AWS Auto Scaling to automatically scale resources based on demand
- Leverage Amazon Elastic Load Balancing to distribute traffic across resources
- Implement asynchronous event-driven architectures to decouple components

#### Monitoring
- Configure Amazon CloudWatch to monitor key reliability metrics
- Leverage AWS CloudTrail to audit changes made to your environment
- Implement a centralized logging solution using Amazon CloudWatch Logs

### Example
Here is an example of how to implement Reliability best practices using AWS services:

1. **Foundations**:
   - Design a multi-AZ, multi-region network topology using Amazon VPC
   - Leverage AWS Auto Scaling to automatically scale EC2 instances in response to changes in demand
   - Use AWS CloudFormation to define your infrastructure as code and enable consistent, repeatable deployments

2. **Change Management**:
   - Implement a CI/CD pipeline using AWS CodePipeline, AWS CodeBuild, and AWS CodeDeploy
   - Utilize blue/green or canary deployment strategies to roll out application updates
   - Integrate with AWS CloudWatch and AWS Lambda to automatically trigger rollbacks on deployment failures

3. **Failure Management**:
   - Design your system with fault-tolerant components that can recover from failures
   - Use Amazon SQS and Amazon SNS to decouple components and handle asynchronous events
   - Implement circuit breakers and retry logic in your application code to handle transient failures

4. **Scaling**:
   - Configure AWS Auto Scaling groups to automatically scale EC2 instances based on metrics like CPU utilization
   - Leverage Elastic Load Balancing to distribute traffic across your scaling resources
   - Implement event-driven architectures using AWS Lambda and Amazon DynamoDB Streams to handle spikes in demand

5. **Monitoring**:
   - Set up Amazon CloudWatch alarms to monitor key reliability metrics like instance health, error rates, and resource utilization
   - Leverage AWS CloudTrail to track changes made to your AWS environment
   - Centralize logging using Amazon CloudWatch Logs and ship logs to a SIEM or analytics solution

By following these design principles and leveraging the appropriate AWS services, you can achieve a high degree of Reliability in your cloud-based systems.

## Performance Efficiency

The Performance Efficiency pillar includes the ability to use computing resources efficiently to meet system requirements, and to maintain that efficiency as demand changes and technologies evolve.

### Design Principles

The key design principles for Performance Efficiency in the AWS Well-Architected Framework are:

1. **Democratize advanced technologies**: Make advanced technologies available to your teams so you don't need to build them yourself.
2. **Go global in minutes**: Use the global availability and low latency of the AWS Cloud to serve users from the closest possible point.
3. **Use serverless architectures**: Remove the need for you to run and maintain servers to carry out traditional compute activities.
4. **Experiment more often**: Try new things, and then measure their impact to gain confidence in your approach.
5. **Mechanical sympathy**: Use the right AWS services for your workload. Consider the technology and patterns that are most optimal.

### Key Areas

The key areas of Performance Efficiency in the AWS Well-Architected Framework are:

#### Selection
- Choose the most appropriate AWS services and resource types for your workload
- Leverage AWS service features like auto scaling, caching, and read replicas
- Consider compute, storage, and database options that best fit your requirements

#### Review
- Continuously monitor your workload performance and identify optimization opportunities
- Experiment with new AWS services and features to improve efficiency
- Analyze cost, latency, throughput, and other relevant metrics

#### Monitoring
- Configure Amazon CloudWatch to monitor performance metrics for your workload
- Leverage AWS X-Ray to trace requests and identify performance bottlenecks
- Integrate with third-party monitoring and observability solutions as needed

#### Tradeoffs
- Understand the various performance, cost, and reliability tradeoffs for each AWS service
- Architect your system to balance performance, cost, and reliability requirements
- Leverage managed services where possible to offload operational overhead

### Example
Here is an example of how to implement Performance Efficiency best practices using AWS services:

1. **Selection**:
   - Choose the appropriate EC2 instance type and size based on your workload requirements
   - Leverage Amazon RDS for managed database services, selecting the right engine and instance class
   - Use Amazon ElastiCache for in-memory data stores to improve read performance
   - Implement caching strategies using Amazon CloudFront and Amazon ElastiCache

2. **Review**:
   - Configure Amazon CloudWatch to monitor key performance metrics like CPU utilization, network throughput, and database connections
   - Analyze AWS X-Ray traces to identify performance bottlenecks in your application
   - Experiment with new AWS services and features, such as Graviton-based EC2 instances or AWS Lambda with provisioned concurrency

3. **Monitoring**:
   - Set up Amazon CloudWatch alarms to alert on performance issues, such as high CPU utilization or increasing latency
   - Leverage AWS CloudTrail to track changes that may impact performance, such as scaling events or configuration updates
   - Integrate with a third-party monitoring solution like Datadog or New Relic to gain deeper visibility into your workload

4. **Tradeoffs**:
   - Evaluate the performance, cost, and reliability tradeoffs when selecting AWS services
   - Use Amazon EBS for storage-intensive workloads, but consider Amazon S3 for static content or data lakes
   - Implement asynchronous processing using Amazon SQS or AWS Lambda to offload work from your primary application

By following these design principles and leveraging the appropriate AWS services, you can achieve a high degree of Performance Efficiency in your cloud-based systems.

## Cost Optimization

The Cost Optimization pillar includes the ability to run systems to deliver business value at the lowest price point.

### Design Principles

The key design principles for Cost Optimization in the AWS Well-Architected Framework are:

1. **Adopt a consumption model**: Pay only for the computing resources you consume, and increase or decrease usage depending on business requirements, rather than having to ahead of time.
2. **Measure overall efficiency**: Track and monitor the cost of your cloud infrastructure, and continuously look for ways to optimize costs.
3. **Stop spending money on undifferentiated heavy lifting**: Eliminate unneeded resources and optimize your costs around the core capabilities of your application.
4. **Analyze and attribute expenditure**: Ensure that you can accurately attribute IT costs to the business and maintain accountability.
5. **Use managed services to reduce cost of ownership**: Take advantage of AWS-managed services to reduce the operational overhead associated with self-managed solutions.

### Key Areas

The key areas of Cost Optimization in the AWS Well-Architected Framework are:

#### Cost-Effective Resources
- Leverage the most cost-effective resources for your workload
- Implement elastic scaling to match resource usage to demand
- Use AWS cost management tools to optimize resource utilization

#### Expenditure Awareness
- Track and allocate costs to specific business units or projects
- Implement budgets and alarms to monitor for unexpected costs
- Perform regular cost reviews and identify optimization opportunities

#### Cost-Effective Services
- Use managed services wherever possible to reduce operational overhead
- Leverage AWS cost optimization features like Amazon EBS optimization
- Consider AWS savings plans and reserved instances to reduce computing costs

#### Matching Supply and Demand
- Implement auto scaling to automatically provision and deprovision resources
- Use spot instances for non-critical workloads to take advantage of discounted pricing
- Leverage serverless services like AWS Lambda to pay only for what you use

#### Continuous Improvement
- Analyze cost and usage data to identify optimization opportunities
- Experiment with new AWS services and features to improve efficiency
- Implement a process to regularly review and optimize your costs

### Example
Here is an example of how to implement Cost Optimization best practices using AWS services:

1. **Cost-Effective Resources**:
   - Choose the most cost-effective EC2 instance types and sizes for your workload
   - Leverage Amazon EBS optimization features to reduce storage costs
   - Implement AWS Auto Scaling to automatically scale resources up and down based on demand

2. **Expenditure Awareness**:
   - Set up AWS Cost Explorer to track and visualize your monthly spend
   - Create AWS Budgets to monitor for unexpected cost increases and receive alerts
   - Use AWS Cost and Usage Report to allocate costs to individual business units or projects

3. **Cost-Effective Services**:
   - Migrate to managed services like Amazon RDS, Amazon DynamoDB, and AWS Lambda to reduce operational overhead
   - Leverage AWS Savings Plans and Reserved Instances to lock in long-term compute discounts
   - Use AWS Fargate to run containerized applications without managing EC2 instances

4. **Matching Supply and Demand**:
   - Implement AWS Auto Scaling to automatically scale EC2 instances based on demand
   - Use Amazon EC2 Spot Instances for non-critical workloads to take advantage of discounted pricing
   - Leverage serverless services like AWS Lambda to pay only for the