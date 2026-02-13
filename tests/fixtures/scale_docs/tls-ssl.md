---
title: Technical Overview of TLS/SSL Connections
description: Detailed technical documentation on the TLS/SSL handshake, certificate chains, cipher suites, mutual TLS, certificate pinning, and OCSP stapling.
keywords: [TLS, SSL, handshake, certificate, cipher suite, mutual TLS, certificate pinning, OCSP stapling]
category: networking
tags: [TLS, SSL, security, encryption, certificates]
---

## TLS/SSL Handshake

The TLS (Transport Layer Security) handshake is the process by which a client and server establish a secure, encrypted connection. The handshake involves the following steps:

1. **Client Hello**: The client sends a `ClientHello` message to the server, which includes the TLS version, a list of supported cipher suites, a list of compression methods, and a random value.

```
Client Hello:
  TLS Version: TLS 1.2
  Cipher Suites: TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384, TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384, ...
  Compression Methods: null
  Random Value: 32-byte random value
```

2. **Server Hello**: The server responds with a `ServerHello` message, which includes the selected TLS version, cipher suite, compression method, and a random value.

```
Server Hello:
  TLS Version: TLS 1.2
  Cipher Suite: TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384
  Compression Method: null
  Random Value: 32-byte random value
```

3. **Server Certificate**: The server sends its X.509 certificate chain to the client.

```
Server Certificate:
  Server's Public Key Certificate
  Intermediate CA Certificate
  Root CA Certificate
```

4. **Server Key Exchange**: If the selected cipher suite uses ephemeral Diffie-Hellman key exchange, the server sends a `ServerKeyExchange` message with its Diffie-Hellman parameters.

5. **Server Hello Done**: The server indicates the end of the handshake negotiation with a `ServerHelloDone` message.

6. **Client Key Exchange**: The client generates a pre-master secret and encrypts it with the server's public key (from the server's certificate). The client sends this encrypted pre-master secret in a `ClientKeyExchange` message.

7. **Change Cipher Spec**: The client sends a `ChangeCipherSpec` message to indicate that all future messages will be encrypted using the negotiated cipher suite and keys.

8. **Client Finished**: The client sends a `Finished` message, which is the first encrypted message using the negotiated keys.

9. **Change Cipher Spec**: The server sends a `ChangeCipherSpec` message to indicate that all future messages will be encrypted.

10. **Server Finished**: The server sends a `Finished` message, which is the first encrypted message using the negotiated keys.

At this point, the TLS handshake is complete, and the client and server can exchange encrypted application data.

## Certificate Chains

SSL/TLS certificates are organized in a hierarchical trust model called a certificate chain. A certificate chain consists of the following elements:

1. **End-entity (leaf) Certificate**: This is the certificate presented by the server (or client in the case of mutual TLS) to the connecting client (or server).

2. **Intermediate CA Certificates**: These are the intermediate Certificate Authority (CA) certificates that signed the end-entity certificate. There can be one or more intermediate CA certificates in the chain.

3. **Root CA Certificate**: This is the self-signed root CA certificate that ultimately vouches for the trust of the entire certificate chain.

The certificate chain is sent by the server (or client) during the TLS handshake so that the connecting party can verify the trust of the presented certificate.

Example certificate chain:

```
End-entity (Leaf) Certificate
  Issued by: Intermediate CA 1
  Valid: 2022-01-01 to 2023-01-01

Intermediate CA 1 Certificate
  Issued by: Intermediate CA 2
  Valid: 2020-01-01 to 2025-01-01

Intermediate CA 2 Certificate
  Issued by: Root CA
  Valid: 2015-01-01 to 2030-01-01

Root CA Certificate
  Self-signed
  Valid: 2010-01-01 to 2040-01-01
```

The client (or server in mutual TLS) verifies the certificate chain by:

1. Verifying the self-signed root CA certificate against its trusted root CA certificates.
2. Verifying each intermediate CA certificate in the chain was signed by the next higher CA certificate.
3. Verifying the end-entity (leaf) certificate was signed by the last intermediate CA certificate.

If the entire chain is successfully verified, the client (or server) can trust the end-entity certificate.

## Cipher Suites

A cipher suite is a combination of algorithms used for encryption, message authentication, and key exchange in a TLS/SSL connection. Common cipher suite naming conventions include:

- `TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384`
  - Key exchange: Ephemeral Elliptic Curve Diffie-Hellman (ECDHE)
  - Authentication: ECDSA
  - Encryption: AES-256 in GCM mode
  - MAC: SHA-384

- `TLS_RSA_WITH_AES_128_CBC_SHA256`
  - Key exchange: RSA
  - Authentication: RSA
  - Encryption: AES-128 in CBC mode
  - MAC: SHA-256

The client sends a list of supported cipher suites in the `ClientHello` message during the TLS handshake. The server then selects the most secure cipher suite from the client's list that it also supports.

Example cipher suite configuration in Nginx:

```nginx
ssl_ciphers TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384:TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384:TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305_SHA256:TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305_SHA256:TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256:TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256;
ssl_prefer_server_ciphers on;
```

In this example, the server will prefer the ECDHE-ECDSA and ECDHE-RSA cipher suites with AES-256-GCM or ChaCha20-Poly1305 encryption and SHA-384 or SHA-256 MAC.

## Mutual TLS

Mutual TLS (mTLS) is a TLS/SSL handshake where both the client and the server authenticate each other using certificates. The process is as follows:

1. **Client Hello**: The client sends a `ClientHello` message, as in the standard TLS handshake.

2. **Server Hello, Certificate, Server Key Exchange**: The server responds with a `ServerHello`, its certificate chain, and a `ServerKeyExchange` message (if needed), as in the standard TLS handshake.

3. **Certificate Request**: The server sends a `CertificateRequest` message to the client, asking the client to present its certificate.

4. **Client Certificate**: The client sends its own certificate chain to the server.

5. **Client Key Exchange**: The client generates a pre-master secret and encrypts it with the server's public key, as in the standard TLS handshake.

6. **Client Verify**: The client sends a `CertificateVerify` message, which is a digital signature over the handshake messages using the client's private key.

7. **Change Cipher Spec, Client Finished**: The client sends a `ChangeCipherSpec` message and a `Finished` message, as in the standard TLS handshake.

8. **Change Cipher Spec, Server Finished**: The server sends a `ChangeCipherSpec` message and a `Finished` message, as in the standard TLS handshake.

In mutual TLS, both the client and the server authenticate each other using their respective certificates. This provides stronger security guarantees compared to one-way SSL/TLS, where only the server is authenticated.

Example Nginx configuration for mutual TLS:

```nginx
ssl_client_certificate /path/to/ca.crt;
ssl_verify_client on;
```

## Certificate Pinning

Certificate pinning is a security technique where a client (e.g., a web browser or mobile app) hard-codes the expected certificate or certificate chain for a specific server. This helps prevent man-in-the-middle attacks where an attacker presents a different, malicious certificate.

There are two main types of certificate pinning:

1. **Public Key Pinning**: The client hard-codes the expected public key of the server's certificate.
2. **Certificate Pinning**: The client hard-codes the expected full certificate or certificate chain of the server.

Example public key pinning in a web browser's Content Security Policy (CSP):

```
Content-Security-Policy: pin-sha256="base64encodedpublickey=="
```

Example certificate pinning in an Android app's network security configuration:

```xml
<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
    <pin-set>
        <pin digest="SHA-256">base64encodedcertificatehash</pin>
    </pin-set>
</network-security-config>
```

Certificate pinning is a powerful security measure, but it can be difficult to manage, as any changes to the server's certificate will require updating the pinned information on all client applications. This can be especially challenging for widely distributed applications.

## OCSP Stapling

OCSP (Online Certificate Status Protocol) Stapling is a TLS/SSL extension that allows the server to provide the client with a signed OCSP response during the TLS handshake. This OCSP response proves that the server's certificate has not been revoked.

In a standard OCSP workflow:

1. The client initiates a TLS handshake with the server.
2. The server sends its certificate chain to the client.
3. The client checks the certificate status by sending an OCSP request to the OCSP responder.
4. The OCSP responder sends a signed OCSP response back to the client.
5. The client verifies the OCSP response and continues the TLS handshake if the certificate is valid.

With OCSP Stapling:

1. The server proactively obtains an OCSP response for its certificate from the OCSP responder.
2. The server "staples" this OCSP response to the TLS handshake, sending it to the client along with the certificate chain.
3. The client verifies the OCSP response without having to make a separate request to the OCSP responder.

OCSP Stapling has several benefits:

- **Faster Handshakes**: The client does not need to make a separate OCSP request, reducing latency.
- **Better Privacy**: The client's OCSP requests are not visible to the OCSP responder, improving privacy.
- **Reduced Load on OCSP Responders**: The server handles the OCSP requests, reducing the load on the OCSP responder.

Example Nginx configuration for OCSP Stapling:

```nginx
ssl_stapling on;
ssl_stapling_verify on;
ssl_trusted_certificate /path/to/ca.crt;
```

In this example, Nginx is configured to enable OCSP Stapling and to verify the OCSP response using the trusted CA certificate.