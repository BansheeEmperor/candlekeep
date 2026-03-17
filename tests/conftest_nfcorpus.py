"""NFCorpus benchmark fixture for graph augmentation tests."""
import json
import re
from collections import defaultdict
from pathlib import Path

import pytest

NFCORPUS = Path(__file__).parent / "fixtures/beir/nfcorpus"


def load_nfcorpus(max_docs: int = 3633):
    """Load NFCorpus. Returns (corpus, queries, qrels)."""
    corpus = {}
    with open(NFCORPUS / "corpus.jsonl") as f:
        for i, line in enumerate(f):
            if i >= max_docs:
                break
            d = json.loads(line)
            corpus[d["_id"]] = d

    queries = {}
    with open(NFCORPUS / "queries.jsonl") as f:
        for line in f:
            d = json.loads(line)
            queries[d["_id"]] = d["text"]

    qrels = {}
    with open(NFCORPUS / "qrels/test.tsv") as f:
        next(f)
        for line in f:
            qid, cid, score = line.strip().split()
            qrels.setdefault(qid, {})[cid] = int(score)

    return corpus, queries, qrels


def _bootstrap_biomedical_ruler(corpus: dict, output_path: Path) -> int:
    """Build entity ruler JSONL from NFCorpus term frequencies.

    Extracts biomedical terms (substances, diseases, conditions) that appear
    in ≥5 documents. These replace the _tech_tokens patterns which only match
    CamelCase/SCREAMING_SNAKE identifiers.
    """
    word_re = re.compile(r"[a-z][a-z\-]{2,}")
    doc_freq: dict[str, set[str]] = defaultdict(set)

    for doc_id, doc in corpus.items():
        text = (doc.get("title", "") + " " + doc.get("text", "")).lower()
        for w in set(word_re.findall(text)):
            doc_freq[w].add(doc_id)

    # Curated biomedical entity vocabulary — only include terms actually in corpus
    BIOMEDICAL = {
        "statin", "statins", "cholesterol", "insulin", "glucose", "vitamin",
        "antioxidant", "antioxidants", "curcumin", "turmeric", "polyphenol",
        "polyphenols", "flavonoid", "flavonoids", "fiber", "folate",
        "calcium", "iron", "zinc", "selenium", "magnesium", "potassium",
        "carotenoid", "carotenoids", "lycopene", "resveratrol", "quercetin",
        "catechin", "isoflavone", "isoflavones", "sulforaphane", "capsaicin",
        "probiotic", "probiotics", "prebiotic", "prebiotics",
        "cancer", "tumor", "tumour", "carcinoma", "melanoma", "leukemia",
        "lymphoma", "diabetes", "hypertension", "obesity", "atherosclerosis",
        "osteoporosis", "alzheimer", "parkinson", "dementia", "stroke",
        "asthma", "allergy", "inflammation", "arthritis", "hepatitis",
        "cirrhosis", "cardiovascular", "coronary", "myocardial", "endothelial",
        "liver", "kidney", "pancreas", "colon", "prostate", "ovarian", "lung",
        "breast", "colorectal", "gastric", "esophageal", "cervical",
        "apoptosis", "angiogenesis", "metastasis", "proliferation",
        "biomarker", "biomarkers", "cytokine", "cytokines", "interleukin",
        "adiponectin", "leptin", "homocysteine", "triglyceride", "triglycerides",
        "hemoglobin", "albumin", "creatinine",
        "mediterranean", "vegetarian", "vegan", "gluten",
        "soybean", "flaxseed", "garlic", "ginger", "cinnamon", "cocoa",
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output_path.open("w") as f:
        for term in sorted(BIOMEDICAL):
            if len(doc_freq.get(term, set())) >= 5:
                f.write(json.dumps({"label": "BIOMED", "pattern": term}) + "\n")
                count += 1
    return count


@pytest.fixture(scope="module")
def nfcorpus_store(tmp_path_factory):
    """Isolated ChromaDB seeded with NFCorpus + biomedical entity ruler + graph."""
    import os
    from candlekeep.config import Settings
    from candlekeep.database.vector_store import ChromaVectorStore
    from candlekeep.database.interface import Chunk
    from candlekeep.database.graph_store import GraphStore, clear_graph_store_cache
    from candlekeep.rag.extractor import clear_extractor_cache

    os.environ["CANDLEKEEP_GRAPH_AUGMENT"] = "true"

    tmp = tmp_path_factory.mktemp("nfcorpus_bench")
    settings = Settings.from_env()
    settings.data_dir = tmp
    for d in ["models", "chroma"]:
        (tmp / d).mkdir(parents=True, exist_ok=True)

    store = ChromaVectorStore(settings)
    coll_name = f"nfcorpus_{tmp.name}"
    store.collection = store.client.get_or_create_collection(
        name=coll_name, metadata={"hnsw:space": "cosine"},
    )

    # 1. Load corpus
    corpus, _, _ = load_nfcorpus()

    # 2. Bootstrap biomedical entity ruler
    ruler_path = settings.entity_ruler_path
    n_patterns = _bootstrap_biomedical_ruler(corpus, ruler_path)
    print(f"\nEntity ruler: {n_patterns} biomedical patterns")

    # 3. Clear caches so extractor picks up new ruler
    clear_graph_store_cache()
    clear_extractor_cache()

    # 4. Set up isolated graph store
    import candlekeep.database.graph_store as gs_mod
    gs = GraphStore(settings.graph_db_path)
    gs_mod._graph_store = gs

    # 5. Ingest (add_documents extracts entities via ruler + stores in graph)
    chunks = [
        Chunk(
            text=f"{d.get('title', '')}. {d.get('text', '')}".strip(),
            metadata={"source": doc_id, "filename": f"{doc_id}.txt"},
            chunk_index=0,
        )
        for doc_id, d in corpus.items()
    ]
    store.add_documents(chunks)

    # 6. Synchronous co-occurrence rebuild
    gs.rebuild_cooccurrence()
    stats = gs.get_stats()
    print(f"Graph: {stats}")

    yield store, gs, settings, corpus

    # Cleanup
    gs_mod._graph_store = None
    clear_extractor_cache()
    try:
        store.client.delete_collection(coll_name)
    except Exception:
        pass
