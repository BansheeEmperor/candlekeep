import os
import json
from datasets import load_dataset
from pathlib import Path

def download_and_map_musique():
    base_dir = Path("tests/fixtures/beir/musique")
    qrels_dir = base_dir / "qrels"
    base_dir.mkdir(parents=True, exist_ok=True)
    qrels_dir.mkdir(parents=True, exist_ok=True)

    print("Loading MuSiQue from HuggingFace (Path: 'dgslibisey/MuSiQue')...")
    ds = load_dataset("dgslibisey/MuSiQue", "default", split="train")
    
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
        
        # Supporting documents
        # MuSiQue rows have 'paragraphs' where 'is_supporting' is True/False
        for para in row["paragraphs"]:
            doc_id = f"{para['title']}_{para['idx']}".replace(" ", "_").lower()
            text = para["paragraph_text"]
            
            if doc_id not in corpus:
                corpus[doc_id] = {"_id": doc_id, "title": para['title'], "text": text}
            
            if para["is_supporting"]:
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

    print("SUCCESS: MuSiQue mapped to BEIR structure.")

if __name__ == "__main__":
    download_and_map_musique()
