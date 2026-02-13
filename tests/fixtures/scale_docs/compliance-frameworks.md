---
title: Compliance Frameworks Overview
description: Detailed technical overview of major compliance frameworks including SOC 2, ISO 27001, PCI DSS, HIPAA, and GDPR requirements and controls.
keywords: 
  - compliance
  - security
  - SOC 2
  - ISO 27001
  - PCI DSS
  - HIPAA
  - GDPR
category: Security
tags:
  - compliance
  - security
  - framework
  - SOC 2
  - ISO 27001
  - PCI DSS
  - HIPAA
  - GDPR
---

## SOC 2

SOC 2 (System and Organization Controls 2) is a compliance framework developed by the American Institute of CPAs (AICPA) that focuses on controls related to security, availability, processing integrity, confidentiality, and privacy of data. It is a widely adopted standard for service organizations and cloud providers.

### SOC 2 Trust Principles

The SOC 2 framework is based on 5 trust principles:

1. **Security**: Controls to protect the system and data from unauthorized access, use, disclosure, disruption, modification, or destruction.
2. **Availability**: Controls to ensure the system is available for operation and use as committed or agreed upon.
3. **Processing Integrity**: Controls to ensure the system processes data accurately, completely, timely, and appropriately.
4. **Confidentiality**: Controls to protect confidential information from being disclosed to unauthorized parties.
5. **Privacy**: Controls to protect personal information from unauthorized access, use, retention, disclosure, deletion, or modification.

### SOC 2 Compliance Requirements

To achieve SOC 2 compliance, organizations must implement controls across these 5 trust principles. Common controls include:

- **Access Management**: Implementing strong access controls, multi-factor authentication, and access reviews.
- **Logging and Monitoring**: Enabling comprehensive logging and monitoring of user activity, system events, and security incidents.
- **Change Management**: Establishing a formal change management process to control modifications to the system.
- **Vulnerability Management**: Regularly scanning for vulnerabilities and patching systems in a timely manner.
- **Incident Response**: Defining and testing an incident response plan to handle security incidents.
- **Backup and Disaster Recovery**: Implementing robust backup and disaster recovery procedures to ensure data and system availability.
- **Risk Assessment**: Conducting periodic risk assessments to identify and mitigate risks.
- **Vendor Management**: Vetting and monitoring third-party service providers that handle sensitive data.
- **Security Awareness Training**: Providing security awareness training to all employees.

### SOC 2 Reporting

There are two types of SOC 2 reports:

1. **SOC 2 Type 1**: Evaluates the design of an organization's controls at a specific point in time.
2. **SOC 2 Type 2**: Evaluates the design and operating effectiveness of an organization's controls over a period of time (typically 6-12 months).

Organizations can choose to report on all 5 trust principles or a subset, depending on their specific business requirements.

## ISO 27001

ISO 27001 is an information security management system (ISMS) standard published by the International Organization for Standardization (ISO). It provides a framework for establishing, implementing, maintaining, and continually improving an organization's information security management system.

### ISO 27001 Requirements

The ISO 27001 standard consists of the following key requirements:

1. **Context of the Organization**: Understanding the organization and its context, including internal and external issues that can affect the ISMS.
2. **Leadership**: Demonstrating leadership and commitment to the ISMS, defining roles and responsibilities, and communicating the importance of the ISMS.
3. **Planning**: Conducting risk assessments, identifying risks, and planning actions to address risks and opportunities.
4. **Support**: Providing the necessary resources, competence, awareness, and communication to support the ISMS.
5. **Operation**: Implementing and controlling the ISMS, including operational planning and control, and changes to the ISMS.
6. **Performance Evaluation**: Monitoring, measuring, analyzing, and evaluating the ISMS to determine its effectiveness.
7. **Improvement**: Addressing nonconformities and continually improving the ISMS.

The standard also includes an extensive set of security controls organized into 14 domains, such as access control, cryptography, physical security, and supplier relationships.

### ISO 27001 Certification

To become ISO 27001 certified, organizations must undergo an external audit by an accredited certification body. The certification process involves:

1. Establishing an ISMS based on the requirements of the ISO 27001 standard.
2. Conducting a comprehensive risk assessment and implementing controls to mitigate identified risks.
3. Undergoing a formal certification audit by an accredited certification body.
4. Maintaining and continually improving the ISMS to retain the certification.

ISO 27001 certification provides independent validation that an organization has implemented a robust information security management system.

## PCI DSS

PCI DSS (Payment Card Industry Data Security Standard) is a compliance framework developed by the PCI Security Standards Council to ensure the secure handling of cardholder data by merchants and service providers who accept, process, store, or transmit credit card information.

### PCI DSS Requirements

The PCI DSS standard consists of 12 high-level requirements, each with various sub-requirements:

1. **Install and maintain a firewall configuration to protect cardholder data**
   - Establish firewall and router configurations
   - Implement a firewall at each internet connection and between any demilitarized zone (DMZ) and the internal network zone
2. **Do not use vendor-supplied defaults for system passwords and other security parameters**
   - Change vendor-supplied defaults before installing a system on the network
   - Develop configuration standards for all system components
3. **Protect stored cardholder data**
   - Protect all stored cardholder data
   - Truncate card numbers so only the last four digits are visible when displayed
4. **Encrypt transmission of cardholder data across open, public networks**
   - Use strong cryptography and security protocols to safeguard sensitive cardholder data during transmission
5. **Protect all systems against malware and regularly update anti-virus software or programs**
   - Deploy anti-virus software on all systems commonly affected by malware
   - Ensure that all anti-virus mechanisms are current, actively running, and generating logs
6. **Develop and maintain secure systems and applications**
   - Establish a process to identify security vulnerabilities and apply applicable patches and updates in a timely manner
7. **Restrict access to cardholder data by business need to know**
   - Limit access to system components and cardholder data to only those individuals whose job requires such access
8. **Identify and authenticate access to system components**
   - Assign a unique ID to each person with computer access
   - Implement multi-factor authentication for remote access to the network
9. **Restrict physical access to cardholder data**
   - Use appropriate facility entry controls to limit and monitor physical access to systems
   - Develop procedures to help all personnel easily distinguish between onsite personnel and visitors
10. **Track and monitor all access to network resources and cardholder data**
    - Implement audit trails to link all access to system components to each individual user
    - Regularly review logs for all system components related to cardholder data
11. **Regularly test security systems and processes**
    - Ensure that security policies and operational procedures for monitoring all access to network resources and cardholder data are documented, in use, and known to all affected parties
    - Implement processes to test for the presence of wireless access points and detect and identify all authorized and unauthorized wireless access points
12. **Maintain a policy that addresses information security for all personnel**
    - Establish, publish, maintain, and disseminate a security policy
    - Review the security policy at least annually and update the policy when the environment changes

### PCI DSS Compliance Requirements

To achieve PCI DSS compliance, organizations must:

1. Assess their environment and document the cardholder data flow.
2. Implement the required security controls and document their compliance with the PCI DSS requirements.
3. Undergo an annual assessment by a qualified security assessor (QSA) or internal auditor to validate their compliance.
4. Maintain compliance and undergo regular self-assessments.

Failing to comply with PCI DSS can result in significant fines, penalties, and the potential loss of the ability to process credit card payments.

## HIPAA

HIPAA (Health Insurance Portability and Accountability Act) is a US federal law that establishes standards for the protection of electronic protected health information (ePHI) handled by healthcare organizations and their business associates.

### HIPAA Rules

The HIPAA regulations consist of several rules, the most relevant being:

1. **HIPAA Privacy Rule**: Establishes standards for the protection of individually identifiable health information.
2. **HIPAA Security Rule**: Establishes standards for the security of electronic protected health information (ePHI).
3. **HIPAA Breach Notification Rule**: Requires covered entities and business associates to provide notification following a breach of unsecured protected health information.

### HIPAA Security Rule Requirements

The HIPAA Security Rule consists of administrative, physical, and technical safeguards that organizations must implement to protect the confidentiality, integrity, and availability of ePHI. Some key requirements include:

**Administrative Safeguards**:
- Implementing security management processes, such as risk analysis and risk management
- Assigning security responsibility to a designated security official
- Establishing workforce security controls, including background checks and access authorization
- Implementing security awareness and training programs for all workforce members

**Physical Safeguards**:
- Implementing physical access controls to limit physical access to ePHI
- Implementing policies and procedures to properly dispose of electronic media containing ePHI
- Implementing a facility security plan to protect the facility and the equipment therein from unauthorized physical access, tampering, and theft

**Technical Safeguards**:
- Implementing access controls to restrict access to ePHI to only authorized individuals or entities
- Implementing audit controls to record and examine activity in information systems that contain or use ePHI
- Implementing mechanisms to encrypt and decrypt ePHI

### HIPAA Compliance Requirements

To achieve HIPAA compliance, organizations must:

1. Conduct a comprehensive risk assessment to identify risks and vulnerabilities to ePHI.
2. Implement the required administrative, physical, and technical safeguards to protect ePHI.
3. Document their HIPAA compliance efforts, including policies, procedures, and implementation details.
4. Train all workforce members on HIPAA requirements and their role in protecting ePHI.
5. Establish and maintain business associate agreements with any third-party service providers that handle ePHI.
6. Implement a breach notification process to promptly report any unauthorized access, use, or disclosure of ePHI.

Failure to comply with HIPAA can result in significant fines and penalties, as well as potential criminal liability.

## GDPR

The General Data Protection Regulation (GDPR) is a comprehensive data privacy and security law enacted by the European Union (EU) that regulates the processing of personal data of individuals within the EU.

### GDPR Key Principles

The GDPR is based on the following key principles:

1. **Lawfulness, Fairness, and Transparency**: Personal data must be processed lawfully, fairly, and in a transparent manner.
2. **Purpose Limitation**: Personal data must be collected for specified, explicit, and legitimate purposes and not further processed in a manner that is incompatible with those purposes.
3. **Data Minimization**: Personal data must be adequate, relevant, and limited to what is necessary in relation to the purposes for which they are processed.
4. **Accuracy**: Personal data must be accurate and, where necessary, kept up to date.
5. **Storage Limitation**: Personal data must be kept in a form that permits identification of data subjects for no longer than is necessary for the purposes for which the personal data are processed.
6. **Integrity and Confidentiality**: Personal data must be processed in a manner that ensures appropriate security of the personal data, including protection against unauthorized or unlawful processing and against accidental loss, destruction, or damage, using appropriate technical or organizational measures.
7. **Accountability**: The controller must be responsible for, and be able to demonstrate compliance with, the GDPR principles.

### GDPR Requirements

The GDPR imposes several key requirements on organizations that process personal data of EU residents, including:

1. **Lawful Basis for Processing**: Identifying a lawful basis for processing personal data, such as consent, contract, legal obligation, vital interest, public task, or legitimate interest.
2. **Data Subject Rights**: Providing data subjects with various rights, such as the right to access, rectify, erase, or port their personal data, and the right to object to or restrict processing.
3. **Data Protection by Design and Default**: Implementing appropriate technical and organizational measures to protect personal data, such as data minimization, pseudonymization, and encryption.
4. **Data Protection Impact Assessments**: Conducting assessments to identify and mitigate risks to the rights and freedoms of data subjects for high-risk processing activities.
5. **Data Breach Notification**: Notifying the relevant supervisory authority and affected data subjects in the event of a personal data breach, unless the breach is unlikely to result in a risk to the rights and freedoms of the data subjects.
6. **Appointment of a Data Protection Officer**: Designating a data protection officer (DPO) if the core activities of the organization involve large-scale processing of sensitive personal data or systematic monitoring of data subjects.
7. **International Data Transfers**: Implementing appropriate safeguards, such as standard contractual clauses or binding corporate rules, for the transfer of personal data outside the European Economic Area.

### GDPR Compliance

To achieve GDPR compliance, organizations must:

1. Conduct a comprehensive data mapping exercise to identify all personal data they collect, process, and store.
2. Implement appropriate technical and organizational measures to ensure the protection of personal data, such as access controls, encryption, and secure data storage and transfer.
3. Establish policies and procedures to handle data subject rights, data breach notifications, and international data transfers.
4. Provide clear and transparent information to data subjects about the processing of their personal data.
5. Appoint a data protection officer if required and ensure regular GDPR audits and risk assessments.
6. Train all employees on GDPR requirements and their roles and responsibilities in protecting personal data.

Failure to comply with GDPR can result in significant fines of up to 4% of an organization's global annual revenue or €20 million (whichever is greater), as well as potential lawsuits and reputational damage.