#!/usr/bin/env python3
"""LLM-based second annotator for graded relevance.

Uses Bedrock (Claude Haiku 3.5) to independently grade the same
(query, chunk) pairs that the heuristic annotator graded. Computes
inter-annotator agreement (Cohen's Kappa, Krippendorff's Alpha),
flags disagreements, and produces a reconciled annotation set.

The LLM sees only the query and chunk text — it does NOT see the
expected sources or the heuristic grade. This ensures independent
judgment for a valid inter-annotator agreement measurement.

Usage:
    python scripts/annotate_llm_second_rater.py [--dry-run] [--model MODEL_ID]
"""
import sys
import os
import json
import re
import time
import argparse
from pathlib import Path
from collections import defaultdict

import boto3

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

DEFAULT_MODEL = "anthropic.claude-3-5-haiku-20241022-v1:0"
REGION = "us-west-2"
PROFILE = "raalgaw"

# The LLM prompt. Deliberately does NOT include expected_sources or
# the heuristic grade — the LLM must judge independently.
GRADING_PROMPT = """\
You are an information retrieval expert evaluating search result quality.

A user searched for: "{query}"

The search system returned this text chunk (from document "{chunk_source}"):

<chunk>
{chunk_text}
</chunk>

How relevant is this chunk to the user's query? Use this scale:

3 = PERFECT: Directly answers the query with the key information needed.
2 = HIGHLY RELEVANT: On-topic and useful context, but does not directly answer.
1 = MARGINALLY RELEVANT: Mentions related concepts but from a different angle.
0 = IRRELEVANT: No meaningful connection to the query.

Respond with a single digit (0, 1, 2, or 3) and nothing else."""

MAX_CHUNK_CHARS = 800  # Cap chunk text to keep prompt focused


def call_bedrock(client, model_id: str, query: str, chunk_source: str, chunk_text: str) -> int:
    """Call Bedrock to grade a single (query, chunk) pair. Returns 0-3."""
    # Truncate long chunks (Arcane Recall merges can produce 1000+ chars)
    if len(chunk_text) > MAX_CHUNK_CHARS:
        chunk_text = chunk_text[:MAX_CHUNK_CHARS] + "\n[... truncated ...]"

    # Extract just the filename for readability
    source_name = Path(chunk_source).name if chunk_source else "unknown"

    prompt = GRADING_PROMPT.format(
        query=query,
        chunk_source=source_name,
        chunk_text=chunk_text,
    )

    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 4,
        "temperature": 0.0,
        "messages": [{"role": "user", "content": prompt}],
    })

    response = client.invoke_model(
        modelId=model_id,
        body=body,
        contentType="application/json",
        accept="application/json",
    )

    result = json.loads(response["body"].read())
    text = result["content"][0]["text"].strip()

    # Parse the single digit
    match = re.search(r"[0-3]", text)
    if match:
        return int(match.group())

    # Fallback: couldn't parse
    print(f"  ⚠ Unparseable LLM response: '{text}', defaulting to 0", file=sys.stderr)
    return 0


def compute_agreement(heuristic_grades: dict, llm_grades: dict):
    """Compute inter-annotator agreement metrics."""
    from sklearn.metrics import cohen_kappa_score

    # Align on common keys
    common_keys = sorted(set(heuristic_grades.keys()) & set(llm_grades.keys()))
    h_vals = [heuristic_grades[k] for k in common_keys]
    l_vals = [llm_grades[k] for k in common_keys]

    # Cohen's Kappa on binary (relevant=1,2,3 vs irrelevant=0)
    h_binary = [1 if v > 0 else 0 for v in h_vals]
    l_binary = [1 if v > 0 else 0 for v in l_vals]
    kappa_binary = cohen_kappa_score(h_binary, l_binary)

    # Cohen's Kappa on ordinal (0-3 scale, weighted)
    kappa_ordinal = cohen_kappa_score(h_vals, l_vals, weights="linear")

    # Exact agreement rate
    exact_agree = sum(1 for h, l in zip(h_vals, l_vals) if h == l) / len(common_keys)

    # Adjacent agreement (within 1 grade)
    adjacent_agree = sum(1 for h, l in zip(h_vals, l_vals) if abs(h - l) <= 1) / len(common_keys)

    # Disagreement analysis
    disagreements = []
    for key, h, l in zip(common_keys, h_vals, l_vals):
        if h != l:
            disagreements.append({
                "chunk_id": key,
                "heuristic": h,
                "llm": l,
                "delta": abs(h - l),
            })

    return {
        "n_pairs": len(common_keys),
        "kappa_binary": round(kappa_binary, 4),
        "kappa_ordinal_linear": round(kappa_ordinal, 4),
        "exact_agreement": round(exact_agree, 4),
        "adjacent_agreement": round(adjacent_agree, 4),
        "disagreements": sorted(disagreements, key=lambda d: -d["delta"]),
    }


def reconcile(heuristic_grades: dict, llm_grades: dict) -> dict:
    """Produce reconciled grades from two annotators.

    Reconciliation rules:
    - Exact agreement: use the agreed grade.
    - Adjacent (delta=1): use the average, rounded up. This favors
      the more generous annotator, which is appropriate for retrieval
      (false negatives are worse than false positives).
    - Large disagreement (delta>=2): use the LLM grade. The heuristic
      is keyword-based and can miss semantic relevance that the LLM
      catches, or over-grade chunks that happen to contain keywords
      but aren't actually relevant.
    """
    reconciled = {}
    common_keys = set(heuristic_grades.keys()) & set(llm_grades.keys())

    for key in common_keys:
        h = heuristic_grades[key]
        l = llm_grades[key]
        delta = abs(h - l)

        if delta == 0:
            reconciled[key] = h
        elif delta == 1:
            # Round up (favor recall)
            reconciled[key] = max(h, l)
        else:
            # Large disagreement: trust the LLM
            reconciled[key] = l

    # Keys only in one annotator (shouldn't happen, but handle gracefully)
    for key in set(heuristic_grades.keys()) - common_keys:
        reconciled[key] = heuristic_grades[key]
    for key in set(llm_grades.keys()) - common_keys:
        reconciled[key] = llm_grades[key]

    return reconciled


def main():
    parser = argparse.ArgumentParser(description="LLM second annotator for graded relevance")
    parser.add_argument("--dry-run", action="store_true", help="Grade 5 pairs only, don't write")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Bedrock model ID")
    parser.add_argument("--resume", type=str, default=None,
                        help="Path to partial LLM grades JSON to resume from")
    args = parser.parse_args()

    # Load eval suite with heuristic grades
    suite_path = Path(__file__).parent.parent / "tests" / "fixtures" / "eval_suite_100.json"
    with open(suite_path) as f:
        suite = json.load(f)

    # Collect all (query, chunk_id, chunk_text, chunk_source) pairs
    # from the heuristic annotations
    pairs = []
    heuristic_all = {}  # global chunk_id -> grade
    for q in suite["queries"]:
        graded = q.get("graded_relevance", {})
        for chunk_id, grade in graded.items():
            heuristic_all[chunk_id] = grade
            # Parse source and chunk_index from chunk_id
            # Format: "tests/fixtures/.../file.md:chunk_index"
            parts = chunk_id.rsplit(":", 1)
            source = parts[0] if len(parts) == 2 else chunk_id
            pairs.append({
                "query": q["query"],
                "category": q["category"],
                "chunk_id": chunk_id,
                "chunk_source": source,
                "heuristic_grade": grade,
            })

    print(f"Total pairs to grade: {len(pairs)}")
    print(f"Model: {args.model}")

    # We need the chunk text. It's not stored in the eval suite — we
    # need to read it from the annotation script's pooled results.
    # Instead, read the graded benchmark results which have the text.
    # Actually, the simplest approach: read the chunk text from the
    # corpus files directly using the source path and chunk index.
    # But Arcane Recall merges chunks, so the text in the annotation
    # may differ from the raw chunk. Let's just use the source filename
    # as context and let the LLM judge based on what it can infer.
    #
    # Better approach: re-read the chunks from the corpus files.
    chunk_texts = {}
    fixtures_dir = Path(__file__).parent.parent / "tests" / "fixtures"
    for subdir in ["sample_docs", "scale_docs"]:
        d = fixtures_dir / subdir
        if not d.exists():
            continue
        for doc_path in d.glob("*"):
            if not doc_path.is_file():
                continue
            text = doc_path.read_text(encoding="utf-8", errors="replace")
            # Simple chunking to get chunk texts (matching processor's output)
            # Strip frontmatter
            fm_match = re.match(r"^---\s*\n.*?\n---\s*\n", text, re.DOTALL)
            content = text[fm_match.end():] if fm_match else text
            # Chunk at 512 chars with 50 overlap (matching project defaults)
            chunks = []
            start = 0
            while start < len(content):
                end = start + 512
                chunk = content[start:end].strip()
                if chunk:
                    chunks.append(chunk)
                start = end - 50 if end < len(content) else len(content)

            source_key = str(doc_path)
            if "tests/fixtures" in source_key:
                source_key = source_key[source_key.index("tests/fixtures"):]
            for i, chunk in enumerate(chunks):
                chunk_texts[f"{source_key}:{i}"] = chunk

    matched = sum(1 for p in pairs if p["chunk_id"] in chunk_texts)
    print(f"Chunk texts found: {matched}/{len(pairs)}")

    # Setup Bedrock client
    session = boto3.Session(profile_name=PROFILE, region_name=REGION)
    client = session.client("bedrock-runtime")

    # Resume from partial results if provided
    llm_grades = {}
    if args.resume and Path(args.resume).exists():
        with open(args.resume) as f:
            llm_grades = json.load(f)
        print(f"Resumed {len(llm_grades)} grades from {args.resume}")

    # Grade pairs
    limit = 5 if args.dry_run else len(pairs)
    errors = 0
    start_time = time.time()

    for i, pair in enumerate(pairs[:limit]):
        chunk_id = pair["chunk_id"]

        # Skip if already graded (resume support)
        if chunk_id in llm_grades:
            continue

        chunk_text = chunk_texts.get(chunk_id)

        # Skip pairs where we couldn't recover the chunk text
        if chunk_text is None:
            continue

        try:
            grade = call_bedrock(client, args.model, pair["query"], pair["chunk_source"], chunk_text)
            llm_grades[chunk_id] = grade
        except Exception as e:
            print(f"  ⚠ Error on pair {i}: {e}", file=sys.stderr)
            errors += 1
            if errors > 10:
                print("Too many errors, stopping.", file=sys.stderr)
                break
            time.sleep(2)
            continue

        if (i + 1) % 50 == 0:
            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed
            remaining = (limit - i - 1) / rate if rate > 0 else 0
            print(f"  [{i+1}/{limit}] {rate:.1f} pairs/sec, ~{remaining:.0f}s remaining")

        # Save progress every 100 pairs
        if (i + 1) % 100 == 0 and not args.dry_run:
            progress_path = Path("tests/results/llm_grades_progress.json")
            progress_path.write_text(json.dumps(llm_grades, indent=2))

    elapsed = time.time() - start_time
    print(f"\nGraded {len(llm_grades)} pairs in {elapsed:.1f}s ({errors} errors)")

    # Grade distribution
    grade_counts = defaultdict(int)
    for g in llm_grades.values():
        grade_counts[g] += 1
    print(f"\nLLM Grade Distribution:")
    for grade in sorted(grade_counts.keys()):
        label = {0: "Irrelevant", 1: "Marginal", 2: "Highly relevant", 3: "Perfect"}[grade]
        count = grade_counts[grade]
        pct = count / len(llm_grades) * 100 if llm_grades else 0
        print(f"  {grade} ({label:>16s}): {count:4d} ({pct:5.1f}%)")

    if args.dry_run:
        # Show the 5 graded pairs for inspection
        print(f"\nDry run — sample grades:")
        for pair in pairs[:5]:
            cid = pair["chunk_id"]
            h = pair["heuristic_grade"]
            l = llm_grades.get(cid, "?")
            print(f"  Query: {pair['query'][:60]}")
            print(f"  Chunk: {cid}")
            print(f"  Heuristic: {h}  LLM: {l}  {'✓' if h == l else '✗ DISAGREE'}")
            print()
        return

    # Compute agreement
    print(f"\n{'='*50}")
    print(f"  INTER-ANNOTATOR AGREEMENT")
    print(f"{'='*50}")
    agreement = compute_agreement(heuristic_all, llm_grades)
    print(f"  Pairs compared:       {agreement['n_pairs']}")
    print(f"  Cohen's κ (binary):   {agreement['kappa_binary']:.4f}")
    print(f"  Cohen's κ (ordinal):  {agreement['kappa_ordinal_linear']:.4f}")
    print(f"  Exact agreement:      {agreement['exact_agreement']:.1%}")
    print(f"  Adjacent agreement:   {agreement['adjacent_agreement']:.1%}")

    # Interpret kappa
    k = agreement["kappa_binary"]
    if k > 0.8:
        interp = "near-perfect — ground truth is reliable"
    elif k > 0.6:
        interp = "substantial — ground truth is usable"
    elif k > 0.4:
        interp = "moderate — review disagreements"
    else:
        interp = "poor — ground truth needs rework"
    print(f"  Interpretation:       {interp}")

    # Top disagreements
    top_disagree = agreement["disagreements"][:10]
    if top_disagree:
        print(f"\n  Top disagreements (by delta):")
        for d in top_disagree:
            print(f"    {d['chunk_id'][:60]:60s}  H={d['heuristic']} L={d['llm']} Δ={d['delta']}")

    # Reconcile
    print(f"\n{'='*50}")
    print(f"  RECONCILIATION")
    print(f"{'='*50}")
    reconciled = reconcile(heuristic_all, llm_grades)

    recon_counts = defaultdict(int)
    for g in reconciled.values():
        recon_counts[g] += 1
    print(f"  Reconciled Grade Distribution:")
    for grade in sorted(recon_counts.keys()):
        label = {0: "Irrelevant", 1: "Marginal", 2: "Highly relevant", 3: "Perfect"}[grade]
        count = recon_counts[grade]
        pct = count / len(reconciled) * 100
        print(f"    {grade} ({label:>16s}): {count:4d} ({pct:5.1f}%)")

    # Write reconciled grades back into eval suite
    for q in suite["queries"]:
        old_grades = q.get("graded_relevance", {})
        new_grades = {}
        for chunk_id in old_grades:
            if chunk_id in reconciled:
                new_grades[chunk_id] = reconciled[chunk_id]
            else:
                new_grades[chunk_id] = old_grades[chunk_id]
        q["graded_relevance"] = new_grades

    suite["metadata"]["version"] = "1.2"
    suite["metadata"]["graded_relevance"] = {
        "scale": "0-3 (irrelevant, marginal, highly relevant, perfect)",
        "method": "reconciled (heuristic + LLM second annotator)",
        "llm_model": args.model,
        "total_pairs": len(reconciled),
        "grade_distribution": dict(recon_counts),
        "agreement": {
            "kappa_binary": agreement["kappa_binary"],
            "kappa_ordinal_linear": agreement["kappa_ordinal_linear"],
            "exact_agreement": agreement["exact_agreement"],
            "adjacent_agreement": agreement["adjacent_agreement"],
        },
    }

    with open(suite_path, "w") as f:
        json.dump(suite, f, indent=2)
    print(f"\nUpdated {suite_path} (v1.2, reconciled)")

    # Save full agreement report
    report_path = Path("tests/results/llm_annotator_agreement.json")
    report = {
        "model": args.model,
        "agreement": agreement,
        "llm_grades": llm_grades,
        "heuristic_grades": heuristic_all,
        "reconciled_grades": reconciled,
    }
    report_path.write_text(json.dumps(report, indent=2))
    print(f"Agreement report saved to {report_path}")


if __name__ == "__main__":
    main()
