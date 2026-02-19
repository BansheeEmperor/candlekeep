#!/usr/bin/env python3
"""Generate a high-redundancy AWS corpus via Amazon Bedrock (Claude).

Creates 3 topic clusters × 5 docs each, where each doc covers the same
core topic from a different angle (tutorial, reference, troubleshooting,
migration, architecture). Also generates a query file with expected sources.

Usage:
  aws sso login --sso-session amzn   # authenticate first
  python scripts/generate_redundant_corpus.py [--model MODEL_ID] [--region REGION]

Output:
  tests/fixtures/redundant_docs/*.md
  tests/fixtures/redundant_docs/eval_queries.json
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

OUTPUT_DIR = Path(__file__).parent.parent / "tests" / "fixtures" / "redundant_docs"

TOPICS = {
    "jwt": {
        "label": "JWT Authentication",
        "angles": [
            ("jwt-tutorial", "How to Implement JWT Authentication",
             "A step-by-step tutorial for implementing JWT authentication in a web application. "
             "Cover generating tokens with a secret key, setting claims (sub, exp, iat), "
             "sending tokens in the Authorization Bearer header, validating tokens on the server, "
             "and handling token expiry. Use Node.js/Express code examples with jsonwebtoken library."),
            ("jwt-reference", "JWT Token Structure and Validation Reference",
             "A technical reference for JWT structure: header (alg, typ), payload (registered claims "
             "like sub, exp, iat, iss, aud; custom claims), signature (HMAC-SHA256, RS256). "
             "Cover Base64URL encoding, token validation steps, signature verification, "
             "and claim validation. Include examples of decoding tokens."),
            ("jwt-troubleshooting", "Debugging JWT Authentication Errors",
             "A troubleshooting guide for common JWT problems: 'jwt malformed' errors, "
             "'TokenExpiredError', 'invalid signature', clock skew issues, wrong algorithm errors, "
             "missing Bearer prefix, CORS issues with Authorization header. "
             "Include debugging steps and code fixes for each error."),
            ("jwt-migration", "Migrating from Session-Based Auth to JWT",
             "A migration guide for replacing server-side sessions with JWT tokens. "
             "Cover removing session middleware, implementing token generation on login, "
             "replacing session checks with token validation middleware, handling refresh tokens, "
             "and managing the transition period where both systems run. Include before/after code."),
            ("jwt-security", "JWT Security Best Practices",
             "A security hardening guide for JWT: choosing RS256 over HS256 for distributed systems, "
             "short expiry times (15 min access, 7 day refresh), secure token storage (httpOnly cookies "
             "vs localStorage), token revocation strategies (blacklist, token versioning), "
             "preventing JWT attacks (none algorithm, key confusion, token sidejacking)."),
            ("jwt-api", "Securing REST APIs with JWT Tokens",
             "A guide to protecting REST API endpoints with JWT. Cover middleware setup for "
             "token validation, role-based access control using JWT claims, protecting specific "
             "routes, handling unauthorized requests (401/403), token refresh endpoints, "
             "and API key vs JWT comparison. Use Express.js middleware examples."),
            ("jwt-microservices", "JWT Authentication in Microservice Architectures",
             "A guide to JWT in microservices: token propagation between services, "
             "centralized vs decentralized token validation, API gateway JWT verification, "
             "service-to-service authentication, token scoping per service, "
             "and handling token refresh across service boundaries."),
            ("jwt-faq", "Common Questions About JWT Authentication",
             "An FAQ covering: Where should I store JWT tokens? How do I handle token refresh? "
             "What happens when a token expires mid-request? How do I revoke a JWT? "
             "Should I use JWT for sessions? What's the difference between access and refresh tokens? "
             "How do I add custom claims? What's the maximum token size?"),
        ],
    },
}

SYSTEM_PROMPT = """\
You are a technical documentation writer. Generate documentation in Markdown format.

Rules:
- Write 500-700 words of content (not counting frontmatter)
- Use the exact frontmatter format shown below
- Include code examples (CLI commands, JSON, or code snippets) where appropriate
- Use ## and ### headings to structure the content
- Be technically accurate and specific
- IMPORTANT: Always use these exact terms throughout the document: JWT, token, claims, \
expiry, signing, verification, Bearer, Authorization header, refresh token, access token, \
secret key, payload, signature, HS256, RS256, jsonwebtoken, middleware, decode, validate. \
This ensures consistent vocabulary across all documents in the series.
- Do NOT include any preamble or explanation outside the document itself

Frontmatter format:
---
title: "<title>"
description: "<one-line description>"
keywords: [<comma-separated keywords in quotes>]
category: "<category>"
tags: [<comma-separated tags in quotes>]
---
"""


def call_bedrock(client, model_id: str, prompt: str) -> str:
    """Call Bedrock with Claude and return the response text."""
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 2048,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
    })

    response = client.invoke_model(
        modelId=model_id,
        contentType="application/json",
        accept="application/json",
        body=body,
    )

    result = json.loads(response["body"].read())
    return result["content"][0]["text"]


def generate_queries(client, model_id: str, doc_manifest: list) -> list:
    """Generate evaluation queries that target overlapping content."""
    manifest_str = "\n".join(
        f"- {d['filename']}: {d['title']} ({d['topic']})" for d in doc_manifest
    )

    prompt = f"""\
Given these documentation files, all covering JWT authentication from different angles:

{manifest_str}

Generate exactly 15 search queries that a developer would ask about JWT authentication.

The key challenge: all documents cover JWT, so queries must be specific enough to have
"best" answers from particular docs, while being general enough that multiple docs are relevant.

Distribution MUST be:
- Exactly 5 EASY queries: each has 1 primary document that answers it best
- Exactly 5 MEDIUM queries: each should be answered by 2 documents that cover overlapping aspects
- Exactly 5 HARD queries: each should be answered by 3 documents covering the topic from different angles

Rules:
- Use category "auth" for all queries
- Every document must appear in at least one query's expected_sources
- expected_sources must use just the filename (e.g., "jwt-tutorial.md"), not full paths
- Queries should use natural developer language, not doc titles

Return ONLY valid JSON, no markdown fences, no explanation:
{{
  "queries": [
    {{
      "query": "the search query",
      "expected_sources": ["filename1.md", "filename2.md"],
      "category": "auth",
      "difficulty": "easy|medium|hard"
    }}
  ]
}}"""

    response = call_bedrock(client, model_id, prompt)

    # Extract JSON from response (handle potential markdown wrapping)
    text = response.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0]

    return json.loads(text)


def main():
    parser = argparse.ArgumentParser(description="Generate redundant AWS corpus via Bedrock")
    parser.add_argument("--model", default="anthropic.claude-3-haiku-20240307-v1:0",
                        help="Bedrock model ID (default: Claude 3 Haiku)")
    parser.add_argument("--region", default="us-east-1",
                        help="AWS region for Bedrock (default: us-east-1)")
    parser.add_argument("--profile", default=None,
                        help="AWS profile name (default: use default credentials)")
    parser.add_argument("--queries-only", action="store_true",
                        help="Skip doc generation, only regenerate eval queries")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    session = boto3.Session(region_name=args.region, profile_name=args.profile)
    client = session.client("bedrock-runtime")

    # Test connectivity
    print(f"🔗 Using model: {args.model} in {args.region}")

    doc_manifest = []
    total = sum(len(t["angles"]) for t in TOPICS.values())

    if args.queries_only:
        # Build manifest from existing files
        print("⏭  Skipping doc generation (--queries-only)")
        for topic_key, topic in TOPICS.items():
            for filename, title, _ in topic["angles"]:
                path = OUTPUT_DIR / f"{filename}.md"
                if path.exists():
                    doc_manifest.append({
                        "filename": f"{filename}.md",
                        "title": title,
                        "topic": topic_key,
                    })
        print(f"   Found {len(doc_manifest)} existing docs")
    else:
        generated = 0
        for topic_key, topic in TOPICS.items():
            print(f"\n📂 Topic: {topic['label']}")
            for filename, title, description in topic["angles"]:
                generated += 1
                print(f"  [{generated}/{total}] Generating {filename}.md ...", end=" ", flush=True)

                prompt = (
                    f"Write a documentation page titled \"{title}\".\n"
                    f"Topic: {topic['label']}\n"
                    f"Angle: {description}\n"
                    f"Category: {topic_key}\n"
                )

                try:
                    content = call_bedrock(client, args.model, prompt)
                    out_path = OUTPUT_DIR / f"{filename}.md"
                    out_path.write_text(content)
                    doc_manifest.append({
                        "filename": f"{filename}.md",
                        "title": title,
                        "topic": topic_key,
                    })
                    print("✓")
                except Exception as e:
                    print(f"✗ {e}")
                    continue

                # Respect rate limits
                time.sleep(1)

    # Generate queries
    print(f"\n📋 Generating evaluation queries...")
    try:
        queries_data = generate_queries(client, args.model, doc_manifest)

        # Fix expected_sources paths to include the fixture directory prefix
        for q in queries_data["queries"]:
            q["expected_sources"] = [
                f"tests/fixtures/redundant_docs/{s}" for s in q["expected_sources"]
            ]

        queries_path = OUTPUT_DIR / "eval_queries.json"
        queries_path.write_text(json.dumps(queries_data, indent=2))
        print(f"   ✓ {len(queries_data['queries'])} queries saved to {queries_path}")
    except Exception as e:
        print(f"   ✗ Query generation failed: {e}")

    print(f"\n✅ Done. {len(doc_manifest)} documents in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
