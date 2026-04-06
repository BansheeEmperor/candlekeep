
import sys
import os
import json
from pathlib import Path
from collections import Counter
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.benchmark_hotpotqa import BenchmarkConfig, load_benchmark_queries
from candlekeep.config import Settings
from candlekeep.database.vector_store import ChromaVectorStore
from candlekeep.rag.extractor import get_extractor
import re

def get_unique_keywords(text, global_counts, top_n=10):
    words = [w.lower() for w in re.findall(r"\w+", text) if len(w) > 4]
    doc_counts = Counter(words)
    scored = {w: count / (1 + global_counts.get(w, 0)) for w, count in doc_counts.items()}
    return sorted(scored.keys(), key=lambda x: scored[x], reverse=True)[:top_n]

async def audit():
    config = BenchmarkConfig(dataset="musique", subset_n=50, path_depth=3, sandbox_size=5000)
    queries = load_benchmark_queries(config)
    
    settings = Settings.from_env()
    settings.data_dir = Path(config.ck_dir)
    db = ChromaVectorStore(settings)
    db.collection = db.client.get_collection(f"{config.dataset}_flagship")
    
    extractor = get_extractor()
    nlp = extractor.nlp

    print("Building global frequency and title map...")
    all_data = db.collection.get()
    global_counts = Counter()
    title_to_text = {}
    
    for text, meta in zip(all_data['documents'], all_data['metadatas']):
        # MuSiQue documents in our sandbox have filenames like 'nike,_inc._7.md'
        # We try to extract the base title
        fname = meta.get('filename', '')
        # Remove _N.md suffix
        title_match = re.sub(r'_\d+\.md$', '', fname)
        title_match = title_match.replace('_', ' ').lower()
        title_to_text[title_match] = text
        
        words = set(re.findall(r"\w+", text.lower()))
        for w in words:
            if len(w) > 4: global_counts[w] += 1

    print(f"Auditing missed hops...")
    divergences = 0
    
    for q in queries:
        required = [t.lower().strip() for t in q['required_titles']]
        if len(required) < 2: continue
        
        # Check current retrieval
        res = db.collection.query(query_texts=[q['query']], n_results=20)
        found_texts = "\n\n".join(res['documents'][0]).lower()
        missing = [t for t in required if t not in found_texts]
        
        if missing:
            divergences += 1
            print(f"\n" + "="*60)
            print(f"QUERY: {q['query']}")
            print(f"MISSING DOCS: {missing}")
            
            # Find the chain: Doc A (found) should lead to Doc B (missing)
            # Or identify the two documents that should be linked
            t1, t2 = required[0], required[1]
            
            # Find closest match in title_to_text for these titles
            def find_text(target):
                for k, v in title_to_text.items():
                    if target in k or k in target:
                        return v
                return None

            txt1 = find_text(t1)
            txt2 = find_text(t2)
            
            if not txt1 or not txt2:
                print(f"    (Could not find sandbox text for '{t1}' or '{t2}')")
                continue

            print(f"  Tracing Link: '{t1}' <--> '{t2}'")
            # Compare techniques
            methods = {
                "Standard NER": lambda t: set(extractor.extract(t)),
                "Noun Chunks": lambda t: {c.text.lower() for c in nlp(t).noun_chunks if len(c.text) > 3},
                "Unique Keywords": lambda t: set(get_unique_keywords(t, global_counts))
            }
            
            for name, func in methods.items():
                ents1 = func(txt1)
                ents2 = func(txt2)
                intersection = ents1 & ents2
                print(f"  Method: {name:15} | Doc A: {len(ents1):3} | Doc B: {len(ents2):3} | Intersection: {intersection}")

        if divergences >= 10: break

if __name__ == "__main__":
    import asyncio
    asyncio.run(audit())
