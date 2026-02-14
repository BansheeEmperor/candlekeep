#!/usr/bin/env python3
"""Test ChromaDB connection and authentication.

Usage:
    python scripts/check_connection.py                          # uses .env
    python scripts/check_connection.py http://localhost:8000     # explicit URL
    python scripts/check_connection.py http://host:8000 TOKEN   # URL + token
"""
import sys
import os

# Load .env if no args
if len(sys.argv) < 2:
    env_file = os.path.join(os.path.dirname(__file__), "..", ".env")
    if os.path.exists(env_file):
        for line in open(env_file):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip().strip('"'))

url = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("CHROMA_URL", "http://localhost:8000")
token = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("CHROMA_AUTH_TOKEN", "")

print(f"Testing connection to: {url}")
print(f"Auth token: {'***' + token[-4:] if token else '(none)'}")
print()

# 1. DNS / network
from urllib.parse import urlparse
parsed = urlparse(url)
host = parsed.hostname
port = parsed.port or 8000

import socket
try:
    ip = socket.gethostbyname(host)
    print(f"✓ DNS resolved: {host} → {ip}")
except socket.gaierror:
    print(f"✗ DNS failed: cannot resolve {host}")
    sys.exit(1)

try:
    sock = socket.create_connection((ip, port), timeout=5)
    sock.close()
    print(f"✓ TCP connected: {ip}:{port}")
except (socket.timeout, ConnectionRefusedError, OSError) as e:
    print(f"✗ TCP failed: {e}")
    print(f"  Check: security group allows your IP, ChromaDB is running on port {port}")
    sys.exit(1)

# 2. HTTP heartbeat
import httpx
headers = {"Authorization": f"Bearer {token}"} if token else {}
try:
    r = httpx.get(f"{url}/api/v2/heartbeat", headers=headers, timeout=5)
    if r.status_code == 200:
        print(f"✓ Heartbeat OK: {r.json()}")
    elif r.status_code == 401:
        print(f"✗ Auth failed (401) — check your token")
        sys.exit(1)
    else:
        print(f"✗ Unexpected status: {r.status_code}")
        sys.exit(1)
except Exception as e:
    print(f"✗ HTTP failed: {e}")
    sys.exit(1)

# 3. Read access
try:
    r = httpx.get(f"{url}/api/v2/tenants/default_tenant", headers=headers, timeout=5)
    if r.status_code == 200:
        print(f"✓ Read access: OK")
    elif r.status_code == 401:
        print(f"✗ Read auth failed (401)")
        sys.exit(1)
    else:
        print(f"✗ Read failed: status {r.status_code}")
        sys.exit(1)
except Exception as e:
    print(f"✗ Read failed: {e}")
    sys.exit(1)

# 4. Write access
try:
    r = httpx.post(f"{url}/api/v2/tenants/default_tenant/databases/default_database/collections",
                   headers={**headers, "Content-Type": "application/json"},
                   json={"name": "__connection_test__"},
                   timeout=5)
    if r.status_code in (200, 201):
        col_id = r.json().get("id", "")
        httpx.delete(f"{url}/api/v2/tenants/default_tenant/databases/default_database/collections/__connection_test__",
                     headers=headers, timeout=5)
        print(f"✓ Write access: OK")
    elif r.status_code == 401:
        print(f"⚠ Write denied (401) — read-only is fine for remote")
    else:
        print(f"⚠ Write check: status {r.status_code} — may be read-only")
except Exception as e:
    print(f"⚠ Write check failed: {e} (read-only is fine for remote)")

print(f"\n✓ All checks passed. Ready to use: CHROMA_URL={url}")
