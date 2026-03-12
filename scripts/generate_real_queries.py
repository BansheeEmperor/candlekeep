"""Generate candidate visual queries for the real corpus.

Captions each diagram with VLM, then outputs a JSON query file.
Queries ask about specific visual details not present in the document text.

Requirements:
  - CANDLEKEEP_VLM_PROVIDER set
  - Corpus generated: python scripts/generate_real_corpus.py

Run: python scripts/generate_real_queries.py
Output: tests/fixtures/real_corpus/eval_real_suite.json (review before benchmarking)
"""
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

CORPUS_DIR = Path("tests/fixtures/real_corpus")
OUT_FILE = CORPUS_DIR / "eval_real_suite.json"

_CAPTION_PROMPT = (
    "You are captioning a technical diagram for a searchable knowledge base. "
    "Describe ALL components, labels, node names, port numbers, values, arrows, "
    "and relationships visible. Be exhaustive and specific — list every label you can read."
)

_QUERY_PROMPT = (
    "Based on this diagram caption, write ONE specific question that:\n"
    "1. Can ONLY be answered by reading this diagram (not from surrounding text)\n"
    "2. Asks about a specific value, component name, port number, or count visible in the diagram\n"
    "3. Is phrased as a natural question an engineer would ask\n"
    "4. Does NOT mention the document title or system name\n\n"
    "Caption:\n{caption}\n\n"
    "Output ONLY the question, nothing else."
)


def main():
    if not os.getenv("CANDLEKEEP_VLM_PROVIDER"):
        print("Error: CANDLEKEEP_VLM_PROVIDER not set")
        sys.exit(1)

    from candlekeep.config import Settings
    from candlekeep.rag.image_captioner import ImageCaptioner
    from candlekeep.providers.factory import create_vision_provider

    settings = Settings.from_env()
    vlm = create_vision_provider()
    captioner = ImageCaptioner(settings, vlm)

    # Try to use LLM for query generation if available
    llm = None
    if os.getenv("CANDLEKEEP_LLM_PROVIDER"):
        try:
            from candlekeep.providers.factory import create_llm_provider
            llm = create_llm_provider()
        except Exception:
            pass

    docs = sorted(CORPUS_DIR.glob("*.md"))
    if not docs:
        print(f"No docs found in {CORPUS_DIR}")
        sys.exit(1)

    # Load existing to allow resuming
    existing = {}
    if OUT_FILE.exists():
        for q in json.loads(OUT_FILE.read_text()):
            existing[q["source"]] = q

    queries = []
    print(f"Generating queries for {len(docs)} docs...\n")

    for i, doc in enumerate(docs, 1):
        source = str(doc)
        if source in existing:
            print(f"  [{i:02d}/{len(docs)}] {doc.name}: skip (cached)")
            queries.append(existing[source])
            continue

        images = captioner.extract_images(doc)
        if not images:
            print(f"  [{i:02d}/{len(docs)}] {doc.name}: no images")
            continue

        print(f"  [{i:02d}/{len(docs)}] {doc.name} ...", end=" ", flush=True)
        try:
            caption = vlm.caption(images[0][0], prompt=_CAPTION_PROMPT, max_tokens=600)
        except Exception as e:
            print(f"FAILED: {e}")
            continue

        if llm:
            try:
                query = llm.complete(_QUERY_PROMPT.format(caption=caption), max_tokens=100).strip()
            except Exception:
                query = "EDIT: What specific component or value is shown in this diagram?"
        else:
            query = "EDIT: What specific component or value is shown in this diagram?"

        entry = {
            "id": f"real_{i:02d}",
            "query": query,
            "expected_sources": [source],
            "category": doc.stem.split("-")[0],
            "reference": caption[:300],
            "needs_review": llm is None,
        }
        queries.append(entry)
        existing[source] = entry

        OUT_FILE.write_text(json.dumps(queries, indent=2))
        print(f"→ {query[:70]}")
        time.sleep(0.3)

    print(f"\n✅ {len(queries)} queries written to {OUT_FILE}")
    if any(q.get("needs_review") for q in queries):
        print("⚠  Some queries need manual review (no LLM provider set)")


if __name__ == "__main__":
    main()
