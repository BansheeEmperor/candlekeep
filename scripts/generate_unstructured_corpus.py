#!/usr/bin/env python3
"""Generate an unstructured-text corpus via Amazon Bedrock (Claude 3 Haiku).

Creates 40 documents with long prose sections and no markdown headers, forcing
the chunker to use fixed-size splitting. Each document is generated in two
passes (Haiku 3 caps at 4096 output tokens) and concatenated to produce
~1500-2500 words per document. Includes overlapping topic pairs to test
retrieval confusability.

Also generates an eval query suite targeting the generated documents.

Usage:
  python scripts/generate_unstructured_corpus.py --profile raalgaw

Output:
  tests/fixtures/unstructured_docs/*.md
  tests/fixtures/unstructured_docs/eval_queries.json
"""
import argparse
import json
import sys
import time
from pathlib import Path

try:
    import boto3
except ImportError:
    print("boto3 required: pip install boto3", file=sys.stderr)
    sys.exit(1)

OUTPUT_DIR = Path(__file__).parent.parent / "tests" / "fixtures" / "unstructured_docs"

SYSTEM_PROMPT = (
    "You are a technical writer producing long-form prose documentation.\n\n"
    "STRICT RULES:\n"
    "1. NO markdown headers (no # symbols anywhere in the output)\n"
    "2. NO bullet lists, numbered lists, or definition lists\n"
    "3. Write ONLY flowing paragraphs separated by blank lines\n"
    "4. Each paragraph must be 5-8 sentences long\n"
    "5. Include specific version numbers, config values, error codes, CLI commands inline\n"
    "6. Use the FULL output length available \u2014 write until you run out of tokens\n"
    "7. Do NOT summarize or conclude early \u2014 keep adding technical detail"
)

# 40 topics across 4 domains. Includes overlapping pairs to test confusability.
# Each tuple: (filename, title, details_csv)
TOPICS = [
    # Networking (10)
    ("net-tcp-tuning", "TCP Performance Tuning for High-Throughput Servers",
     "TCP window scaling, Nagle algorithm, TCP_NODELAY, congestion control cubic vs bbr, "
     "socket buffer sizing with sysctl net.core.rmem_max, TIME_WAIT optimization, "
     "keepalive configuration, MSS negotiation, SYN backlog tuning, zero-copy sendfile"),
    ("net-tcp-debugging", "Debugging TCP Connection Issues in Production",
     "tcpdump capture analysis, Wireshark filters for retransmissions, ss command output, "
     "TCP state machine transitions, RST packet causes, connection timeout diagnosis, "
     "MTU path discovery failures, TCP Fast Open troubleshooting, SACK negotiation"),
    ("net-dns-recursive", "DNS Recursive Resolution and Caching Internals",
     "Recursive vs iterative resolution, DNSSEC validation chain, TTL caching behavior, "
     "negative caching RFC 2308, EDNS0 extensions, DNS over HTTPS configuration, "
     "stub resolver vs full resolver, glue records, delegation chains, root hints"),
    ("net-dns-operations", "Operating DNS Infrastructure at Scale",
     "BIND 9.18 configuration, zone transfer AXFR vs IXFR, TSIG authentication, "
     "response rate limiting, DNS amplification mitigation, anycast routing for DNS, "
     "monitoring query latency with dnstap, DNSSEC key rotation, zone signing"),
    ("net-tls-handshake", "TLS 1.3 Handshake Protocol Deep Dive",
     "ClientHello extensions, key share negotiation, 0-RTT resumption risks, certificate "
     "chain validation, OCSP stapling, cipher suite TLS_AES_256_GCM_SHA384, "
     "session tickets vs PSK, encrypted client hello ECH, post-handshake auth"),
    ("net-tls-operations", "TLS Certificate Operations and Troubleshooting",
     "openssl s_client debugging, certificate chain verification, intermediate CA issues, "
     "HSTS preload list, certificate transparency log monitoring, ACME protocol, "
     "certbot renewal hooks, PEM vs DER encoding, PKCS12 keystores, SNI routing"),
    ("net-load-balancing", "Layer 4 vs Layer 7 Load Balancing Architecture",
     "Connection draining, health check tuning intervals, consistent hashing ring, "
     "least-connections vs round-robin, sticky sessions with cookies, cross-zone "
     "balancing, connection multiplexing, HAProxy vs Envoy, PROXY protocol v2"),
    ("net-http2-internals", "HTTP/2 Stream Multiplexing and Flow Control",
     "Frame types DATA HEADERS SETTINGS, HPACK header compression, flow control windows "
     "WINDOW_UPDATE, stream prioritization, server push, connection coalescing, "
     "GOAWAY handling, h2c upgrade from HTTP/1.1, HTTP/2 in gRPC"),
    ("net-grpc-internals", "gRPC Protocol Internals and Performance Tuning",
     "Protocol Buffers wire format, gRPC channel management, keepalive pings, "
     "max message size configuration, client-side load balancing, deadline propagation, "
     "interceptor chains, reflection service, health checking protocol, channelz"),
    ("net-service-mesh", "Service Mesh Data Plane Architecture",
     "Envoy proxy sidecar injection, xDS API protocol, circuit breaking configuration, "
     "retry budgets, outlier detection, traffic splitting for canary deployments, "
     "mTLS certificate rotation, Istio vs Linkerd, WASM filter extensions"),
    # Databases (10)
    ("db-postgres-vacuum", "PostgreSQL VACUUM and Autovacuum Internals",
     "Dead tuple accumulation, transaction ID wraparound, autovacuum_vacuum_threshold, "
     "autovacuum_vacuum_scale_factor, VACUUM FREEZE, pg_stat_user_tables monitoring, "
     "table bloat estimation, aggressive vacuum, vacuum_cost_delay throttling"),
    ("db-postgres-locks", "PostgreSQL Locking and Concurrency Control",
     "Lock modes ACCESS SHARE through ACCESS EXCLUSIVE, advisory locks, deadlock "
     "detection log_lock_waits, lock timeout, row-level vs table-level locks, "
     "MVCC snapshot isolation, serializable transactions, predicate locks"),
    ("db-index-internals", "B-Tree Index Internals and Optimization",
     "Page splits and fill factor, index-only scans with INCLUDE columns, "
     "covering indexes, partial indexes WHERE clauses, HOT updates, "
     "index bloat pgstattuple, REINDEX CONCURRENTLY, BRIN indexes"),
    ("db-replication-streaming", "PostgreSQL Streaming Replication Setup",
     "WAL shipping configuration, replication slots, pg_stat_replication monitoring, "
     "replay lag vs write lag vs flush lag, synchronous_commit settings, "
     "cascading replicas, pg_basebackup, recovery_target_timeline"),
    ("db-replication-logical", "PostgreSQL Logical Replication and CDC",
     "Publication and subscription setup, pgoutput plugin, wal_level logical, "
     "conflict resolution, initial table sync, DDL replication limitations, "
     "Debezium CDC connector, slot monitoring pg_replication_slots"),
    ("db-connection-pooling", "Connection Pooling with PgBouncer",
     "Transaction vs session vs statement pooling, pool_size tuning, "
     "server_lifetime, client_idle_timeout, prepared statement handling, "
     "auth_type configuration, stats monitoring, SHOW POOLS command"),
    ("db-query-planning", "PostgreSQL Query Planner Cost Estimation",
     "Sequential scan vs index scan cost model, random_page_cost tuning, "
     "effective_cache_size, join strategies nested loop hash merge, "
     "parallel query, JIT compilation thresholds, EXPLAIN ANALYZE BUFFERS"),
    ("db-partitioning", "PostgreSQL Table Partitioning Strategies",
     "Range vs list vs hash partitioning, partition pruning, partition-wise joins, "
     "pg_partman automated management, detach and attach operations, "
     "constraint exclusion, default partition, partition key selection"),
    ("db-redis-internals", "Redis Data Structures and Memory Management",
     "String encoding int embstr raw, ziplist vs listpack, hash-max-ziplist, "
     "memory fragmentation ratio, active defragmentation, maxmemory-policy "
     "eviction, RDB vs AOF persistence, lazy freeing, memory doctor"),
    ("db-redis-cluster", "Redis Cluster Operations and Failover",
     "Hash slot distribution, CLUSTER MEET ADDSLOTS, replica migration, "
     "cluster-node-timeout, manual failover CLUSTER FAILOVER, resharding, "
     "cluster bus protocol, split-brain prevention, cluster-require-full-coverage"),
    # Linux Systems (10)
    ("linux-memory-virtual", "Linux Virtual Memory and Page Tables",
     "Multi-level page tables, TLB misses and flushes, huge pages 2MB 1GB, "
     "transparent huge pages THP, vm.overcommit_memory, OOM killer oom_score_adj, "
     "NUMA topology numactl, memory cgroups v2, KSM page merging"),
    ("linux-memory-profiling", "Linux Memory Profiling and Leak Detection",
     "valgrind memcheck, AddressSanitizer ASAN, /proc/meminfo interpretation, "
     "smaps_rollup per-process RSS, perf mem record, BPF memory tracing, "
     "jemalloc heap profiling, MALLOC_ARENA_MAX, massif visualizer"),
    ("linux-io-scheduler", "Linux I/O Scheduling and Block Layer",
     "mq-deadline vs bfq vs kyber, ionice priorities, direct I/O vs buffered, "
     "readahead tuning blockdev, blktrace analysis, fio benchmarking, "
     "NVMe queue depths, io_uring submission queues, IOPS vs throughput"),
    ("linux-cgroups-v2", "cgroups v2 Resource Control and Systemd Integration",
     "Unified hierarchy, cpu.max bandwidth, memory.max memory.high, "
     "io.max device throttling, delegation to unprivileged users, systemd slices, "
     "pressure stall information PSI, cpu.weight, memory.swap.max"),
    ("linux-networking-stack", "Linux Kernel Networking Stack Internals",
     "NAPI polling, GRO GSO offloading, XDP programs, tc qdisc HTB FQ_CODEL, "
     "netfilter conntrack nf_conntrack_max, socket buffer autotuning, "
     "RSS RPS RFS multi-queue NICs, ethtool ring buffer tuning"),
    ("linux-process-scheduling", "CFS and Real-Time Process Scheduling",
     "Completely Fair Scheduler vruntime, nice values -20 to 19, "
     "SCHED_FIFO vs SCHED_RR, CPU affinity taskset, isolcpus kernel parameter, "
     "NO_HZ_FULL, schedtool, cgroup cpu.max bandwidth control"),
    ("linux-systemd-units", "Systemd Service Management and Unit Files",
     "Unit file Type forking notify, LimitNOFILE, RestartSec restart policies, "
     "socket activation, template units %i, journald log management, "
     "systemd-analyze blame, ProtectSystem PrivateTmp hardening"),
    ("linux-containers-runtime", "Container Runtime Internals and OCI Spec",
     "runc vs crun, OCI runtime spec, container lifecycle hooks, "
     "pivot_root vs chroot, overlay filesystem layers, seccomp BPF profiles, "
     "user namespace mapping, rootless networking slirp4netns, podman"),
    ("linux-ebpf", "eBPF Programming for Observability",
     "BPF program types kprobe tracepoint XDP, bpftool, CO-RE BTF, "
     "BPF maps hash array ringbuf, libbpf skeleton, bpftrace one-liners, "
     "overhead measurement, BPF verifier constraints, BPF LSM hooks"),
    ("linux-perf-analysis", "Linux Performance Analysis with perf",
     "perf stat hardware counters, perf record sampling, flame graphs, "
     "perf annotate instruction-level, perf probe dynamic tracing, "
     "perf lock contention, off-CPU profiling, perf c2c cache analysis"),
    # Security (10)
    ("sec-oauth2-flows", "OAuth 2.0 Authorization Flows and Token Management",
     "Authorization code with PKCE, client credentials grant, device authorization, "
     "token introspection endpoint, refresh token rotation, scope validation, "
     "JWT access tokens RS256, token binding, DPoP proof of possession"),
    ("sec-oauth2-threats", "OAuth 2.0 Security Threats and Mitigations",
     "Authorization code interception, CSRF on redirect URI, token leakage referrer, "
     "mix-up attacks, open redirector exploitation, PKCE downgrade attacks, "
     "DPoP proof of possession, RFC 9126 PAR, token theft via XSS"),
    ("sec-certificate-lifecycle", "X.509 Certificate Lifecycle Management",
     "CSR generation openssl req, CA hierarchy root intermediate, "
     "certificate pinning, CRL vs OCSP, certificate transparency SCT, "
     "ACME certbot renewal, key archival, PEM DER PKCS12 formats"),
    ("sec-container-isolation", "Container Runtime Security Boundaries",
     "Namespace isolation pid net mnt user, seccomp profiles, AppArmor SELinux, "
     "rootless containers user namespaces, read-only root filesystem, "
     "capability dropping CAP_NET_RAW, Falco runtime detection, gVisor"),
    ("sec-secret-rotation", "Secrets Management and Automated Rotation",
     "HashiCorp Vault dynamic secrets, AWS Secrets Manager rotation lambdas, "
     "envelope encryption, transit secrets engine, lease duration tuning, "
     "audit logging, Vault agent auto-auth, secret zero problem"),
    ("sec-zero-trust", "Zero Trust Network Architecture Implementation",
     "Identity-based access, micro-segmentation, continuous verification, "
     "device posture assessment, mutual TLS service mesh, policy decision points, "
     "SPIFFE SPIRE identity, BeyondCorp model, context-aware access"),
    ("sec-supply-chain", "Software Supply Chain Security",
     "SBOM generation syft, vulnerability scanning grype, Sigstore cosign, "
     "SLSA framework levels, in-toto attestations, dependency confusion attacks, "
     "Dependabot Renovate, reproducible builds, provenance verification"),
    ("sec-waf-rules", "Web Application Firewall Rule Engineering",
     "OWASP Core Rule Set CRS 4.0, ModSecurity vs cloud WAF, rate limiting, "
     "SQL injection detection patterns, XSS filter bypass, bot detection "
     "JavaScript challenges, false positive tuning, anomaly scoring"),
    ("sec-incident-response", "Security Incident Response Procedures",
     "NIST SP 800-61 framework, containment strategies, forensic imaging, "
     "chain of custody, IOC extraction, MITRE ATT&CK mapping, "
     "post-incident review, automated response playbooks, SOAR platforms"),
    ("sec-cryptography", "Applied Cryptography for Developers",
     "AES-256-GCM authenticated encryption, RSA vs ECDSA key generation, "
     "Argon2id password hashing, HKDF key derivation, envelope encryption, "
     "libsodium sealed boxes, constant-time comparison, CSPRNG usage"),
]


def call_bedrock(client, model_id, messages, max_tokens=4096):
    """Call Bedrock with Claude messages API and return the response text."""
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "system": SYSTEM_PROMPT,
        "messages": messages,
        "temperature": 0.7,
    })
    response = client.invoke_model(
        modelId=model_id,
        contentType="application/json",
        accept="application/json",
        body=body,
    )
    result = json.loads(response["body"].read())
    return result["content"][0]["text"], result.get("stop_reason", "end_turn")


def generate_document(client, model_id, filename, title, details):
    """Generate a long document using assistant prefill continuation.

    Uses the Anthropic cookbook technique: after the first response hits
    end_turn, feed it back as an assistant message and ask to continue.
    Repeat until we have enough content or 4 passes max.
    """
    category = filename.split("-")[0]
    cat_map = {"net": "networking", "db": "databases",
               "linux": "linux", "sec": "security"}
    cat_label = cat_map.get(category, category)

    user_prompt = (
        f'Write a comprehensive technical document about: {title}\n\n'
        f'Cover ALL of these topics in flowing prose paragraphs: {details}\n\n'
        f'Start with YAML frontmatter:\n'
        f'---\n'
        f'title: "{title}"\n'
        f'description: "<one-line description>"\n'
        f'keywords: [<3-5 keywords in quotes>]\n'
        f'category: "{cat_label}"\n'
        f'---\n\n'
        f'Then write dense technical prose. Each topic above must get its own '
        f'dedicated paragraph of 5-8 sentences with specific version numbers, '
        f'config values, and CLI commands. Do NOT skip any topic.'
    )

    messages = [{"role": "user", "content": user_prompt}]
    full_text = ""

    for pass_num in range(4):
        text, stop = call_bedrock(client, model_id, messages, max_tokens=4096)
        full_text += text
        word_count = len(full_text.split())

        if word_count >= 2000:
            break

        # Prefill continuation: feed response back and ask to continue
        messages.append({"role": "assistant", "content": text})
        messages.append({"role": "user", "content":
            "Continue writing. You have not covered all the topics yet. "
            "Keep writing dense technical paragraphs. Do NOT repeat what "
            "you already wrote. Do NOT add headers or lists."
        })
        time.sleep(0.3)

    return full_text


def generate_queries(client, model_id, doc_manifest):
    """Generate eval queries targeting the unstructured documents."""
    manifest_str = "\n".join(
        f"- {d['filename']}: {d['title']} (category: {d['category']})"
        for d in doc_manifest
    )
    prompt = (
        f'Given these technical documents:\n\n{manifest_str}\n\n'
        f'Generate exactly 60 evaluation queries as a JSON array. Each query should:\n'
        f'1. Target a specific document (use the filename as expected_source)\n'
        f'2. Be a natural question someone would ask\n'
        f'3. Include a mix of:\n'
        f'   - 20 semantic queries (conceptual questions)\n'
        f'   - 20 lexical queries (containing specific version numbers, config params)\n'
        f'   - 20 adversarial queries (topics NOT covered, expected_sources=[])\n\n'
        f'Return ONLY valid JSON:\n'
        f'{{"queries": [{{"query": "...", '
        f'"expected_sources": ["tests/fixtures/unstructured_docs/<filename>.md"], '
        f'"category": "semantic|lexical|adversarial", '
        f'"difficulty": "easy|medium|hard"}}]}}'
    )
    return call_bedrock(client, model_id,
        [{"role": "user", "content": prompt}], max_tokens=8192)[0]


def main():
    parser = argparse.ArgumentParser(
        description="Generate unstructured corpus via Bedrock")
    parser.add_argument("--model",
                        default="anthropic.claude-3-haiku-20240307-v1:0")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--profile", default=None)
    args = parser.parse_args()

    session = boto3.Session(region_name=args.region, profile_name=args.profile)
    client = session.client("bedrock-runtime")

    print("Testing Bedrock connectivity...", end=" ", flush=True)
    try:
        call_bedrock(client, args.model,
                     [{"role": "user", "content": "Say ok"}], max_tokens=10)
        print("OK")
    except Exception as e:
        print(f"FAILED: {e}")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    doc_manifest = []
    total = len(TOPICS)

    for i, (filename, title, details) in enumerate(TOPICS, 1):
        out_path = OUTPUT_DIR / f"{filename}.md"
        if out_path.exists():
            print(f"  [{i}/{total}] {filename} -- exists, skipping")
            word_count = len(out_path.read_text().split())
            doc_manifest.append({
                "filename": filename, "title": title,
                "category": filename.split("-")[0], "words": word_count,
            })
            continue

        print(f"  [{i}/{total}] Generating {filename}...", end=" ", flush=True)
        try:
            content = generate_document(client, args.model, filename,
                                        title, details)
            out_path.write_text(content)
            word_count = len(content.split())
            print(f"{word_count} words")
            doc_manifest.append({
                "filename": filename, "title": title,
                "category": filename.split("-")[0], "words": word_count,
            })
            time.sleep(0.5)
        except Exception as e:
            print(f"FAILED: {e}")
            continue

    # Generate eval queries
    print(f"\nGenerating evaluation queries for {len(doc_manifest)} docs...")
    try:
        raw = generate_queries(client, args.model, doc_manifest)
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0]
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0]
        queries = json.loads(raw)
        queries_path = OUTPUT_DIR / "eval_queries.json"
        queries_path.write_text(json.dumps(queries, indent=2))
        print(f"  {len(queries.get('queries', []))} queries saved")
    except Exception as e:
        print(f"  Query generation failed: {e}")

    # Report
    print(f"\nCorpus summary:")
    print(f"  Documents: {len(doc_manifest)}")
    total_words = sum(d['words'] for d in doc_manifest)
    print(f"  Total words: {total_words:,}")
    print(f"  Avg words/doc: {total_words // max(len(doc_manifest), 1):,}")
    print(f"  Output: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
