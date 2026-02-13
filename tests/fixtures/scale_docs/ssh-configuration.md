---
title: Comprehensive SSH Configuration Guide
description: A detailed technical reference for configuring and managing SSH, including key management, agent forwarding, tunneling, ProxyJump, hardening, and authorized_keys.
keywords: [ssh, configuration, key management, agent forwarding, tunneling, proxyjump, hardening, authorized_keys]
category: system administration
tags: [ssh, security, networking, devops]
---

## SSH Configuration

The SSH (Secure Shell) configuration file, typically located at `~/.ssh/config` on Unix-like systems and `%USERPROFILE%\.ssh\config.exe` on Windows, allows you to define custom settings for connecting to remote hosts. This file can greatly simplify your SSH usage by providing a centralized place to store connection details, default options, and host-specific configurations.

Here's an example `~/.ssh/config` file:

```
Host example
    HostName example.com
    User alice
    IdentityFile ~/.ssh/id_rsa
    Port 22
    
Host github
    HostName github.com
    User git
    IdentityFile ~/.ssh/github_rsa
    
Host *.internal
    User admin
    ProxyCommand ssh bastion.company.com nc %h %p
```

In this example, we've defined three host entries:

1. `example`: Connects to `example.com` as the user `alice` using the `id_rsa` key, and connects on port 22.
2. `github`: Connects to `github.com` as the `git` user using the `github_rsa` key.
3. `*.internal`: Connects to any host with a subdomain of `internal` as the `admin` user, using a ProxyCommand to first connect to the `bastion.company.com` host.

The `Host` directive specifies the hostname pattern to match, while the other configuration options define the connection details.

## Key Management

SSH authentication relies on public-key cryptography, where each user has a pair of keys: a public key and a private key. The public key is shared with the remote servers, while the private key is kept secure on the user's local machine.

### Generating SSH Keys

To generate a new SSH key pair, you can use the `ssh-keygen` command:

```
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
```

This will create a 4096-bit RSA key pair, with the public key stored in `~/.ssh/id_rsa.pub` and the private key in `~/.ssh/id_rsa`.

### Managing Multiple Keys

It's common for users to have multiple SSH keys, each used for different purposes (e.g., personal, work, GitHub, etc.). To manage these keys, you can use the `IdentityFile` option in your `~/.ssh/config` file to specify which key to use for each host:

```
Host github.com
    IdentityFile ~/.ssh/github_rsa

Host example.com
    IdentityFile ~/.ssh/id_rsa
```

This ensures that the correct key is used for each remote host.

### SSH Agent

The SSH agent is a background process that holds your private keys in memory, allowing you to authenticate with remote servers without constantly entering your passphrase. To use the SSH agent:

1. Start the agent: `eval "$(ssh-agent -s)"`
2. Add your key to the agent: `ssh-add ~/.ssh/id_rsa`

Now, when you connect to a remote server, the SSH agent will automatically use the appropriate key to authenticate you, without prompting for the passphrase.

## Agent Forwarding

Agent forwarding allows you to use your local SSH agent to authenticate with remote servers, even when you're connecting through intermediate hosts. This can be useful when you need to access resources on a remote network from your local machine.

To enable agent forwarding, add the following line to your `~/.ssh/config` file:

```
Host *
    ForwardAgent yes
```

Alternatively, you can enable agent forwarding on a per-host basis:

```
Host example.com
    ForwardAgent yes
```

Now, when you connect to a remote server, your local SSH agent will be available, and you can use your keys to authenticate without having to copy them to the remote host.

## Tunneling

SSH tunneling allows you to create secure connections between your local machine and a remote server, effectively forwarding network traffic through the SSH connection. This can be useful for accessing resources on a remote network, bypassing firewalls, or even running a local web server that's accessible from the internet.

### Local Port Forwarding

Local port forwarding maps a local port on your machine to a remote port on the SSH server. For example, to forward your local port 8080 to port 80 on the remote server:

```
ssh -L 8080:example.com:80 user@example.com
```

Now, you can access the remote web server by visiting `http://localhost:8080` on your local machine.

### Remote Port Forwarding

Remote port forwarding maps a remote port on the SSH server to a local port on your machine. This can be useful for accessing a local service from the remote server. For example, to forward remote port 8080 to your local port 80:

```
ssh -R 8080:localhost:80 user@example.com
```

Now, you can access your local web server by connecting to `http://example.com:8080` from the remote server.

### Dynamic Port Forwarding (SOCKS Proxy)

Dynamic port forwarding creates a SOCKS proxy that can be used to forward any network traffic through the SSH connection. This is useful for bypassing firewalls or accessing resources on a remote network.

```
ssh -D 8080 user@example.com
```

After running this command, you can configure your web browser or other applications to use the `localhost:8080` SOCKS proxy, and all network traffic will be routed through the SSH tunnel.

## ProxyJump

The ProxyJump feature in SSH allows you to connect to a remote host by first connecting to an intermediate "jump" host. This is useful when you need to access a host that is only accessible from within a private network, or when you need to go through multiple hops to reach your destination.

Here's an example configuration in `~/.ssh/config`:

```
Host bastion
    HostName bastion.example.com
    User alice

Host internal.example.com
    ProxyJump bastion
    User bob
```

In this case, when you connect to `internal.example.com`, SSH will first connect to the `bastion.example.com` host, and then use that connection to reach the final destination.

```
ssh internal.example.com
```

The ProxyJump feature can be chained to accommodate multiple jump hosts, if necessary.

## Hardening SSH

To improve the security of your SSH setup, you can apply the following hardening measures:

1. **Use Strong Encryption**: In your `~/.ssh/config` file, specify the ciphers, MACs, and key exchange algorithms you want to use:

   ```
   Host *
       Ciphers chacha20-poly1305@openssh.com,aes256-gcm@openssh.com,aes128-gcm@openssh.com,aes256-ctr,aes192-ctr,aes128-ctr
       MACs hmac-sha2-512-etm@openssh.com,hmac-sha2-256-etm@openssh.com,umac-128-etm@openssh.com
       KexAlgorithms curve25519-sha256,curve25519-sha256@libssh.org,diffie-hellman-group16-sha512,diffie-hellman-group18-sha512,diffie-hellman-group-exchange-sha256
   ```

2. **Disable Password Authentication**: To prevent password-based attacks, you can disable password authentication and rely solely on public-key authentication:

   ```
   Host *
       PasswordAuthentication no
       PubkeyAuthentication yes
   ```

3. **Disable Root Login**: Prevent direct root login to your SSH server by adding the following line:

   ```
   Host *
       PermitRootLogin no
   ```

4. **Limit Allowed Users**: You can specify a list of users who are allowed to connect to your SSH server:

   ```
   Host *
       AllowUsers alice bob charlie
   ```

5. **Enable Logging**: Increase the verbosity of SSH logging to help with troubleshooting and security monitoring:

   ```
   Host *
       LogLevel INFO
   ```

6. **Use Trusted DNS**: To prevent man-in-the-middle attacks, you can specify a trusted DNS server in your SSH configuration:

   ```
   Host *
       HashKnownHosts yes
       VerifyHostKeyDNS yes
       PreferredAuthentications publickey
   ```

These are just a few examples of how you can harden your SSH setup. The specific configuration will depend on your security requirements and the environment you're working in.

## authorized_keys File

The `authorized_keys` file is a critical component of SSH authentication, as it stores the public keys of users who are allowed to connect to the remote server. Each line in the `authorized_keys` file represents a single public key, and the file is typically located at `~/.ssh/authorized_keys` on the remote server.

Here's an example of what an `authorized_keys` file might look like:

```
ssh-rsa AAAAB3NzaC1yc2EAA...QAJIk97b9J6LwYZb7odRqzApJg== alice@local-machine
ssh-rsa AAAAB3NzaC1yc2EAA...LnSQxaGiaGNv53Lxk1LGNGQJLc== bob@work-laptop
ssh-ed25519 AAAAC3NzaC1lZD...Jf2G5XxFYzA2SE== charlie@personal-device
```

Each entry consists of the public key type (e.g., `ssh-rsa`, `ssh-ed25519`), the actual public key data, and an optional comment (e.g., the username and/or the hostname of the machine the key was generated on).

To add a new public key to the `authorized_keys` file, you can simply append the key to the file:

```
cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys
```

Alternatively, you can use the `ssh-copy-id` command, which will automatically add the specified key to the remote server's `authorized_keys` file:

```
ssh-copy-id user@remote-host
```

Maintaining the `authorized_keys` file is an essential part of SSH key management, as it controls which users are allowed to connect to the remote server.