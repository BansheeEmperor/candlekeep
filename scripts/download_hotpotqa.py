import os
import json
from datasets import load_dataset
from pathlib import Path

def download_and_map_hotpotqa():
    base_dir = Path("tests/fixtures/beir/hotpotqa")
    qrels_dir = base_dir / "qrels"
    base_dir.mkdir(parents=True, exist_ok=True)
    qrels_dir.mkdir(parents=True, exist_ok=True)

    print("Loading HotpotQA from HuggingFace (Path: 'hotpot_qa')...")
    # Correct path is 'hotpot_qa'
    ds = load_dataset("hotpot_qa", "distractor", split="train")
    
    # Standard BEIR formats
    corpus_file = base_dir / "corpus.jsonl"
    queries_file = base_dir / "queries.jsonl"
    qrels_file = qrels_dir / "test.tsv"

    print("Mapping to BEIR format...")
    corpus = {}
    queries = {}
    qrels = []

    # Process first 500 samples
    for i, row in enumerate(ds.select(range(500))):
        qid = f"q_{i}"
        queries[qid] = row["question"]
        
        relevant_titles = set(row["supporting_facts"]["title"])
        
        for title, sentences in zip(row["context"]["title"], row["context"]["sentences"]):
            doc_id = title.replace(" ", "_").lower()
            text = " ".join(sentences)
            
            if doc_id not in corpus:
                corpus[doc_id] = {"_id": doc_id, "title": title, "text": text}
            
            if title in relevant_titles:
                qrels.append(f"{qid}\t{doc_id}\t1")

    print(f"Writing {len(corpus)} documents to {corpus_file}...")
    with open(corpus_file, "w") as f:
        for doc in corpus.values():
            f.write(json.dumps(doc) + "\n")

    print(f"Writing {len(queries)} queries to {queries_file}...")
    with open(queries_file, "w") as f:
        for qid, qtext in queries.items():
            f.write(json.dumps({"_id": qid, "text": qtext}) + "\n")

    print(f"Writing {len(qrels)} qrels to {qrels_file}...")
    with open(qrels_file, "w") as f:
        f.write("query-id\tcorpus-id\tscore\n")
        for line in qrels:
            f.write(line + "\n")

    print("SUCCESS: HotpotQA mapped to BEIR structure.")

if __name__ == "__main__":
    download_and_map_hotpotqa()
