---
title: Cryptography Fundamentals - Symmetric, Asymmetric, Hashing, KDF
description: A comprehensive technical guide covering the fundamentals of cryptography, including symmetric encryption (AES, ChaCha20), asymmetric encryption (RSA, ECDSA), hashing (SHA-256, bcrypt), and key derivation functions (KDFs).
keywords: 
  - cryptography
  - encryption
  - symmetric
  - asymmetric
  - hashing
  - kdf
  - aes
  - chacha20
  - rsa
  - ecdsa
  - sha256
  - bcrypt
category: Security
tags:
  - cryptography
  - encryption
  - hashing
  - key-derivation
---

## Symmetric Encryption

Symmetric encryption, also known as secret-key cryptography, is a type of encryption where a single shared secret key is used to both encrypt and decrypt data. This is in contrast to asymmetric encryption, where separate public and private keys are used.

The main advantages of symmetric encryption are:

- **Speed**: Symmetric algorithms are generally much faster than asymmetric algorithms, making them well-suited for encrypting large amounts of data.
- **Simplicity**: Symmetric encryption has a simpler key management process compared to asymmetric encryption.

The main disadvantages are:

- **Key Distribution**: The shared secret key must be securely distributed between the communicating parties, which can be challenging.
- **Security Risk**: If the shared key is compromised, all encrypted data is vulnerable.

### AES (Advanced Encryption Standard)

AES is a symmetric-key algorithm adopted as an encryption standard by the U.S. government in 2001. It is one of the most widely used symmetric encryption algorithms today.

AES supports key sizes of 128, 192, and 256 bits, and operates on 128-bit blocks of data. It is an iterative, symmetric-key block cipher that can encrypt and decrypt information.

**AES Key Generation**

AES keys can be generated using a cryptographically secure random number generator (CSPRNG). Here is an example of generating a 256-bit AES key in Python using the `secrets` module:

```python
import secrets

aes_key = secrets.token_bytes(32)  # 256-bit (32 byte) AES key
```

**AES Encryption and Decryption**

Here is an example of AES-256 encryption and decryption in Python using the `cryptography` library:

```python
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

# Encryption
plaintext = b'This is a secret message.'
key = secrets.token_bytes(32)
iv = secrets.token_bytes(16)

cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
encryptor = cipher.encryptor()
ciphertext = encryptor.update(plaintext) + encryptor.finalize()

# Decryption
decryptor = cipher.decryptor()
decrypted_text = decryptor.update(ciphertext) + decryptor.finalize()

print(f'Plaintext: {plaintext.decode()}')
print(f'Ciphertext: {ciphertext.hex()}')
print(f'Decrypted text: {decrypted_text.decode()}')
```

This example uses AES-256 in Cipher Block Chaining (CBC) mode. The `iv` (initialization vector) is used to add randomness to the encryption process and prevent patterns in the ciphertext.

### ChaCha20

ChaCha20 is a high-performance, provably secure, and widely deployed symmetric-key encryption algorithm. It was designed by Daniel Bernstein and is an alternative to AES, particularly in environments where AES hardware acceleration is not available.

ChaCha20 operates on 256-bit keys and 96-bit nonces, and produces 64-bit block ciphers. It is often combined with Poly1305 for additional authentication, forming the ChaCha20-Poly1305 AEAD (Authenticated Encryption with Associated Data) cipher suite.

**ChaCha20 Key Generation**

Similar to AES, ChaCha20 keys can be generated using a CSPRNG. Here is an example in Python:

```python
import secrets

chacha20_key = secrets.token_bytes(32)  # 256-bit (32 byte) ChaCha20 key
```

**ChaCha20 Encryption and Decryption**

Here is an example of ChaCha20 encryption and decryption in Python using the `cryptography` library:

```python
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

# Encryption
plaintext = b'This is a secret message.'
key = secrets.token_bytes(32)
nonce = secrets.token_bytes(12)

cipher = Cipher(algorithms.ChaCha20(key, nonce), mode=None, backend=default_backend())
encryptor = cipher.encryptor()
ciphertext = encryptor.update(plaintext) + encryptor.finalize()

# Decryption
decryptor = cipher.decryptor()
decrypted_text = decryptor.update(ciphertext) + decryptor.finalize()

print(f'Plaintext: {plaintext.decode()}')
print(f'Ciphertext: {ciphertext.hex()}')
print(f'Decrypted text: {decrypted_text.decode()}')
```

This example uses a 256-bit ChaCha20 key and a 96-bit nonce. The nonce should be unique for each encryption operation to ensure the security of the cipher.

## Asymmetric Encryption

Asymmetric encryption, also known as public-key cryptography, is a type of encryption where a pair of keys is used: a public key for encryption and a private key for decryption. This is in contrast to symmetric encryption, where a single shared secret key is used.

The main advantages of asymmetric encryption are:

- **Key Distribution**: Asymmetric encryption simplifies the key distribution process, as the public key can be shared openly without compromising the security of the private key.
- **Non-Repudiation**: Asymmetric encryption can provide digital signatures, which allow for non-repudiation of the sender.

The main disadvantages are:

- **Speed**: Asymmetric algorithms are generally much slower than symmetric algorithms, making them less suitable for encrypting large amounts of data.
- **Key Size**: Asymmetric keys are typically much larger than symmetric keys, requiring more storage and computation.

### RSA (Rivest-Shamir-Adleman)

RSA is one of the earliest and most widely used asymmetric encryption algorithms. It is based on the mathematical problem of finding the factors of large composite numbers.

**RSA Key Generation**

RSA keys are generated using two large prime numbers. Here is an example of generating an RSA key pair in Python using the `cryptography` library:

```python
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

# Generate private key
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
    backend=default_backend()
)

# Extract public key
public_key = private_key.public_key()
```

This example generates a 2048-bit RSA key pair with a public exponent of 65537 (a common choice).

**RSA Encryption and Decryption**

Here is an example of RSA encryption and decryption in Python using the `cryptography` library:

```python
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

# Encryption
plaintext = b'This is a secret message.'
ciphertext = public_key.encrypt(
    plaintext,
    padding.OAEP(
        mgf=padding.MGF1(algorithm=hashes.SHA256()),
        algorithm=hashes.SHA256(),
        label=None
    )
)

# Decryption
decrypted_text = private_key.decrypt(
    ciphertext,
    padding.OAEP(
        mgf=padding.MGF1(algorithm=hashes.SHA256()),
        algorithm=hashes.SHA256(),
        label=None
    )
)

print(f'Plaintext: {plaintext.decode()}')
print(f'Ciphertext: {ciphertext.hex()}')
print(f'Decrypted text: {decrypted_text.decode()}')
```

This example uses OAEP (Optimal Asymmetric Encryption Padding) with SHA-256 for the encryption and decryption operations.

### ECDSA (Elliptic Curve Digital Signature Algorithm)

ECDSA is an asymmetric cryptography algorithm used for digital signatures. It is based on elliptic curve cryptography, which can provide the same level of security as RSA with much smaller key sizes.

**ECDSA Key Generation**

Here is an example of generating an ECDSA key pair in Python using the `cryptography` library:

```python
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend

# Generate private key
private_key = ec.generate_private_key(
    ec.SECP256R1(),
    default_backend()
)

# Extract public key
public_key = private_key.public_key()
```

This example generates a 256-bit ECDSA key pair using the SECP256R1 (also known as P-256) elliptic curve.

**ECDSA Signing and Verification**

Here is an example of ECDSA signing and verification in Python using the `cryptography` library:

```python
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec

# Signing
message = b'This is a signed message.'
signature = private_key.sign(
    message,
    ec.ECDSA(hashes.SHA256())
)

# Verification
try:
    public_key.verify(
        signature,
        message,
        ec.ECDSA(hashes.SHA256())
    )
    print('Signature is valid.')
except InvalidSignature:
    print('Invalid signature.')
```

This example signs a message using the private key and verifies the signature using the public key. The signature is created and verified using the ECDSA algorithm with the SHA-256 hash function.

## Hashing

Hashing is the process of transforming a variable-length input into a fixed-length output, called a hash value or digest. Hashing is a fundamental cryptographic primitive used for various purposes, such as data integrity, password storage, and digital signatures.

The main properties of a cryptographic hash function are:

- **Deterministic**: The same input will always produce the same output.
- **One-way**: It is computationally infeasible to derive the input from the output.
- **Collision-resistant**: It is computationally infeasible to find two different inputs that produce the same output.

### SHA-256 (Secure Hash Algorithm)

SHA-256 is a widely used cryptographic hash function that is part of the SHA-2 family of hash algorithms. It produces a 256-bit (32-byte) hash value.

**SHA-256 Hashing**

Here is an example of computing a SHA-256 hash in Python using the `hashlib` module:

```python
import hashlib

message = b'This is a message to be hashed.'
sha256_hash = hashlib.sha256(message).hexdigest()

print(f'SHA-256 hash: {sha256_hash}')
```

This will output the 64-character hexadecimal representation of the SHA-256 hash of the input message.

### bcrypt

bcrypt is a password hashing function based on the Blowfish cipher. It is designed to be computationally expensive, making it resistant to brute-force and rainbow table attacks.

**bcrypt Hashing**

Here is an example of hashing a password using bcrypt in Python with the `bcrypt` library:

```python
import bcrypt

password = b'MySecurePassword'
salt = bcrypt.gensalt()
hashed_password = bcrypt.hashpw(password, salt)

print(f'Hashed password: {hashed_password.decode()}')
```

The `bcrypt.gensalt()` function generates a salt, which is combined with the password to create the final hash. The salt is stored alongside the hash to allow for password verification later.

**bcrypt Verification**

To verify a password against a stored bcrypt hash, you can use the `bcrypt.checkpw()` function:

```python
import bcrypt

stored_hash = b'$2b$12$...the stored hash...'
input_password = b'MySecurePassword'

if bcrypt.checkpw(input_password, stored_hash):
    print('Password is valid!')
else:
    print('Invalid password.')
```

The `bcrypt.checkpw()` function compares the provided password with the stored hash, returning `True` if they match.

## Key Derivation Functions (KDFs)

Key Derivation Functions (KDFs) are algorithms used to derive one or more secret keys from a secret value, such as a password or a master key. KDFs are essential for secure key management, as they allow you to derive strong, cryptographically secure keys from weaker or less secure sources of entropy.

### PBKDF2 (Password-Based Key Derivation Function 2)

PBKDF2 is a standard KDF specified in IETF RFC 8018. It is designed to be computationally expensive, making it resistant to brute-force attacks.

**PBKDF2 Key Derivation**

Here is an example of using PBKDF2 to derive a key from a password in Python with the `cryptography` library:

```python
import os
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

password = b'MySecurePassword'
salt = os.urandom(16)  # Generate a random salt
iterations = 100000

kdf = PBKDF2HMAC(
    algorithm=hashes.SHA256(),
    length=32,
    salt=salt,
    iterations=iterations,
    backend=default_backend()
)

derived_key = kdf.derive(password)

print(f'Derived key: {derived_key.hex()}')
```

This example uses PBKDF2-HMAC-SHA256 to derive a 32-byte (256-bit) key from the provided password and a random salt. The number of iterations is set to 100,000 to make the key derivation computationally expensive.

### Argon2

Argon2 is a modern, memory-hard KDF that is designed to be resistant to hardware-based attacks, such as GPU-based brute-force attacks. It is the winner of the Password Hashing Competition and is recommended by the OWASP.

**Argon2 Key Derivation**

Here is an example of using Argon2 to derive a key from a password in Python with the `argon2-cffi` library:

```python
import os
from argon2 import PasswordHasher

password = b'MySecurePassword'
salt = os.urandom(16)  # Generate a random salt

ph = PasswordHasher(
    time_cost=2,
    memory_cost=102400,
    parallelism=8,
    hash_len=32,
    salt_len=16
)

derived_key = ph.hash(password)

print(f'Derived key: {derived_key}')
```

This example uses Argon2id (the recommended variant of Argon2) to derive a 32-byte (256-bit) key from the provided password and a random salt. The parameters `time_cost`, `memory_cost`, and `parallelism` can be adjusted to tune the computational cost of the key derivation.

To verify a password against a derived key, you can use the `PasswordHasher.verify()` function:

```python
if ph.verify(derived_key, password):
    print('Password is valid!')
else:
    print('Invalid password.')
```

The `PasswordHasher.verify()` function compares the provided password with the stored derived key, returning `True` if they match.