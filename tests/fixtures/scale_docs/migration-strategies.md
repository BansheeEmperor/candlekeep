---
title: Cloud Migration Strategies
description: Detailed technical guide to cloud migration strategies including rehost, replatform, refactor, repurchase, retire, retain, and assessment methodology.
keywords:
  - cloud migration
  - rehost
  - replatform
  - refactor
  - repurchase
  - retire
  - retain
  - assessment
category: cloud
tags:
  - cloud
  - migration
  - strategy
  - rehost
  - replatform
  - refactor
  - repurchase
  - retire
  - retain
  - assessment
---

## Cloud Migration Strategies

### Rehost ("Lift and Shift")

The rehost strategy, also known as "lift and shift", involves migrating an existing application to the cloud with minimal changes. This is the fastest and easiest cloud migration approach, as it simply moves the application to the cloud infrastructure without any significant modifications.

**Advantages:**
- Shortest migration timeline
- Minimal changes required to application
- Reduced migration risk

**Disadvantages:**
- Limited ability to take advantage of cloud-native features and services
- Applications may not be optimized for the cloud environment
- Ongoing operational costs may be higher than other strategies

**Example:** Migrating an existing virtual machine (VM) running on-premises to an Infrastructure-as-a-Service (IaaS) offering in the cloud, such as Amazon EC2 or Microsoft Azure Virtual Machines, with little to no changes to the application.

### Replatform ("Lift, Tinker and Shift")

The replatform strategy involves making minor changes to an application to take advantage of cloud-native features and services, while still maintaining the core of the application's architecture. This approach is often referred to as "lift, tinker and shift".

**Advantages:**
- Leverages some cloud-native features and services
- Reduced migration effort compared to refactoring
- Improved operational efficiency and cost savings

**Disadvantages:**
- Requires some application modifications
- May not fully optimize the application for the cloud

**Example:** Migrating an on-premises application to a Platform-as-a-Service (PaaS) offering, such as Microsoft Azure App Service or AWS Elastic Beanstalk, and making changes to utilize managed database services, auto-scaling, and other cloud-native features.

### Refactor ("Re-architect")

The refactor strategy involves a significant redesign and re-architecture of an application to take full advantage of cloud-native features and services. This approach is often referred to as "re-architecting" the application.

**Advantages:**
- Fully optimizes the application for the cloud
- Leverages cloud-native features and services
- Improved scalability, performance, and cost-efficiency

**Disadvantages:**
- Requires the most effort and time for migration
- Significant changes to the application's architecture and code

**Example:** Migrating a monolithic application to a microservices-based architecture, leveraging cloud-native services such as managed databases, serverless functions, and container orchestration platforms.

### Repurchase ("Drop and Shop")

The repurchase strategy involves replacing an existing application with a cloud-based commercial off-the-shelf (COTS) solution or software-as-a-service (SaaS) offering. This approach is often referred to as "drop and shop".

**Advantages:**
- Reduced operational overhead and maintenance
- Access to the latest features and functionality
- Potential cost savings compared to maintaining an in-house solution

**Disadvantages:**
- Potential loss of customization and control
- Vendor lock-in
- Data migration challenges

**Example:** Replacing an on-premises customer relationship management (CRM) system with a cloud-based SaaS CRM solution, such as Salesforce or Microsoft Dynamics 365.

### Retire

The retire strategy involves decommissioning applications or workloads that are no longer needed or have been replaced by newer, more efficient solutions.

**Advantages:**
- Reduced operational costs and overhead
- Simplified IT infrastructure and management

**Disadvantages:**
- Potential loss of historical data or functionality

**Example:** Shutting down an legacy application that is no longer in use, as it has been replaced by a more modern, cloud-based solution.

### Retain

The retain strategy involves keeping applications or workloads on-premises, rather than migrating them to the cloud. This approach is often used for applications that are not well-suited for cloud migration, or when the cost or risk of migration outweighs the benefits.

**Advantages:**
- Maintain control and customization of on-premises applications
- Avoid potential issues with cloud migration

**Disadvantages:**
- Ongoing maintenance and operational costs for on-premises infrastructure
- Missing out on cloud-native benefits and cost savings

**Example:** Maintaining an on-premises Enterprise Resource Planning (ERP) system that is highly customized and tightly integrated with other on-premises systems, where the cost and effort of migration is not justified.

### Assessment Methodology

Implementing a thorough assessment methodology is crucial to determine the most appropriate cloud migration strategy for each application or workload. The assessment process typically involves the following steps:

1. **Inventory and Discovery**
   - Identify all applications, systems, and dependencies within the existing IT infrastructure.
   - Gather detailed information about each application, such as architecture, technology stack, performance characteristics, and business criticality.

2. **Application Complexity and Readiness Assessment**
   - Evaluate the complexity of each application, including factors such as customization, integration with other systems, and the use of legacy technologies.
   - Assess the application's readiness for cloud migration, considering factors like cloud-compatibility, data sensitivity, and compliance requirements.

3. **Business and Technical Alignment**
   - Align the cloud migration strategy with the organization's business objectives and technical requirements.
   - Consider factors such as cost optimization, scalability, availability, and the need for specific cloud-native features.

4. **Risk and Dependency Analysis**
   - Identify and mitigate potential risks associated with the cloud migration, such as data security, regulatory compliance, and operational disruptions.
   - Analyze dependencies between applications and systems to ensure a seamless migration process.

5. **Migration Planning and Execution**
   - Develop a detailed migration plan, including timelines, resource requirements, and implementation steps.
   - Execute the migration plan, closely monitoring the process and addressing any issues that arise.

6. **Optimization and Continuous Improvement**
   - Continuously optimize the migrated applications and infrastructure to take full advantage of the cloud's capabilities.
   - Monitor performance, cost, and other relevant metrics, and make adjustments as needed.

Throughout the assessment and migration process, it's essential to involve stakeholders from both the business and IT teams to ensure alignment and successful outcomes.

## Cloud Migration Strategies in Action

### Rehost Example: Migrating a Virtual Machine to the Cloud

Let's consider the example of migrating an on-premises virtual machine (VM) to a cloud-based IaaS offering, such as Amazon EC2 or Microsoft Azure Virtual Machines.

**Steps:**
1. **Inventory and Discovery**: Gather information about the existing VM, including its operating system, installed software, resource utilization, and any dependencies.
2. **Complexity and Readiness Assessment**: Evaluate the VM's suitability for a rehost migration, considering factors like compatibility with the target cloud platform and the need for any modifications.
3. **Migration Planning**: Determine the appropriate cloud instance type and resources required, plan the migration timeline, and ensure any necessary networking or security configurations are in place.
4. **Execution**: Use tools like AWS Server Migration Service or Azure Site Recovery to perform a "lift and shift" migration, transferring the VM to the cloud with minimal changes.
5. **Optimization**: Monitor the migrated VM's performance and cost, and make any necessary adjustments to optimize its operation in the cloud environment.

**Example Commands:**

```
# AWS Server Migration Service (SMS) commands
aws sms-voice-connector list-voice-connectors
aws sms-voice-connector create-voice-connector --name "my-voice-connector" --require-encryption

# Azure Site Recovery commands
asr vault list
asr replication-policy list --vault-name "myVault" --resource-group "myResourceGroup"
asr server-migration create --vault-name "myVault" --resource-group "myResourceGroup" --name "myMigration"
```

### Replatform Example: Migrating a .NET Application to a PaaS Service

Consider the example of migrating an on-premises .NET application to a cloud-based Platform-as-a-Service (PaaS) offering, such as Microsoft Azure App Service or AWS Elastic Beanstalk.

**Steps:**
1. **Inventory and Discovery**: Gather information about the existing .NET application, including its architecture, dependencies, and any cloud-specific configuration requirements.
2. **Complexity and Readiness Assessment**: Evaluate the application's compatibility with the target PaaS platform, identify any necessary modifications, and plan for the integration of cloud-native services.
3. **Migration Planning**: Determine the appropriate PaaS service plan, configure any necessary networking or security settings, and plan for the migration of the application's data and dependencies.
4. **Execution**: Deploy the .NET application to the PaaS platform, making any necessary changes to leverage cloud-native features and services, such as managed databases or auto-scaling.
5. **Optimization**: Monitor the application's performance and cost in the cloud environment, and make any necessary adjustments to optimize its operation, such as scaling resources or integrating additional cloud services.

**Example Configuration:**

```yaml
# Azure App Service configuration (azure-app-service.yml)
apiVersion: web/v1
kind: WebApp
metadata:
  name: my-dotnet-app
spec:
  appName: my-dotnet-app
  resourceGroup: my-resource-group
  plan:
    name: my-app-service-plan
    sku: S1
  runtime:
    dotnet: '6.0'
  config:
    appSettings:
    - name: WEBSITE_LOAD_CERTIFICATES
      value: "*"
    connectionStrings:
    - name: SqlConnection
      connectionString: Server=tcp:my-sql-server.database.windows.net,1433;Initial Catalog=my-database;Persist Security Info=False;User ID=my-admin;Password=my-password;MultipleActiveResultSets=False;Encrypt=True;TrustServerCertificate=False;Connection Timeout=30;
```

### Refactor Example: Migrating a Monolithic Application to Microservices

Consider the example of refactoring a monolithic application to a microservices-based architecture, leveraging cloud-native services and technologies.

**Steps:**
1. **Inventory and Discovery**: Thoroughly analyze the existing monolithic application, identifying its key components, dependencies, and data flows.
2. **Complexity and Readiness Assessment**: Assess the feasibility of refactoring the application, considering factors like the complexity of the codebase, the availability of skilled developers, and the organization's experience with microservices.
3. **Migration Planning**: Define the target microservices architecture, including the individual services, their responsibilities, and the communication patterns between them. Plan the migration process, including the phased decomposition of the monolith and the adoption of cloud-native technologies.
4. **Execution**: Incrementally refactor the monolithic application, breaking it down into smaller, independently deployable microservices. Leverage cloud-native services and technologies, such as managed databases, serverless functions, and container orchestration platforms (e.g., Kubernetes).
5. **Optimization**: Continuously monitor the performance, cost, and scalability of the microservices-based application, making adjustments to the architecture and resource allocations as needed.

**Example Architecture:**

```
+--------------+      +---------------+      +----------------+
|  User-facing |      | Recommendation |      |   Payments     |
|   Service    |      |    Service    |      |    Service     |
+--------------+      +---------------+      +----------------+
       |                      |                       |
       |                      |                       |
+---------------+    +---------------+    +----------------+
|   Catalog     |    |   Inventory   |    |    Analytics   |
|    Service    |    |    Service    |    |     Service    |
+---------------+    +---------------+    +----------------+
       |                      |                       |
       |                      |                       |
+---------------+    +---------------+    +----------------+
|   Database    |    |   Database    |    |    Database    |
|    Service    |    |    Service    |    |     Service    |
+---------------+    +---------------+    +----------------+
```

In this example, the monolithic application has been refactored into a microservices-based architecture, with each service responsible for a specific domain or functionality. The services communicate with each other using well-defined APIs, and they leverage cloud-native services for storage, messaging, and other infrastructure needs.

### Repurchase Example: Migrating from an On-Premises CRM to a SaaS CRM Solution

Consider the example of replacing an on-premises customer relationship management (CRM) system with a cloud-based software-as-a-service (SaaS) CRM solution, such as Salesforce or Microsoft Dynamics 365.

**Steps:**
1. **Inventory and Discovery**: Thoroughly document the existing CRM system, including its features, integrations, data model, and customizations.
2. **Complexity and Readiness Assessment**: Evaluate the suitability of the organization's business processes and data for the target SaaS CRM solution. Identify any potential gaps or required customizations.
3. **Migration Planning**: Develop a comprehensive migration plan, including data migration, user onboarding, integration with other systems, and phased implementation.
4. **Execution**: Deploy the SaaS CRM solution and migrate data from the existing system. Customize the SaaS platform as needed to meet the organization's requirements.
5. **Optimization**: Continuously monitor the SaaS CRM solution's performance, user adoption, and integration with other systems. Make adjustments and additional customizations as necessary.

**Example Configuration:**

```
# Salesforce configuration
{
  "version": "49.0",
  "packageType": "Managed",
  "namespacePrefix": "acme",
  "objects": [
    {
      "name": "Account",
      "fields": [
        {
          "name": "Name",
          "type": "String"
        },
        {
          "name": "Industry",
          "type": "Picklist"
        }
      ]
    },
    {
      "name": "Contact",
      "fields": [
        {
          "name": "FirstName",
          "type": "String"
        },
        {
          "name": "LastName",
          "type": "String"
        }
      ]
    }
  ],
  "tabs": [
    {
      "name": "Accounts",
      "type": "CustomObject",
      "object": "Account"
    },
    {
      "name": "Contacts",
      "type": "CustomObject",
      "object": "Contact"
    }
  ]
}
```

In this example, the Salesforce configuration defines the objects, fields, and tabs that make up the CRM solution, allowing for a seamless migration from the on-premises system.