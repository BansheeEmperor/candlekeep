import pytest
import os
import shutil
import tempfile
from pathlib import Path
from candlekeep.config import Settings
from candlekeep.database.vector_store import ChromaVectorStore
from candlekeep.rag.processor import DocumentProcessor
from candlekeep.rag.router import search_with_routing

pytestmark = [pytest.mark.benchmark]

QUERIES = [
    ("How to store tokens on iOS?", "ios-auth.md"),
    ("Biometric login implementation for Android", "android-auth.md"),
    ("OAuth2 configuration for React apps", "web-auth.md"),
    ("Using Windows Hello in Electron apps", "desktop-auth.md"),
    ("TPM based identity for embedded devices", "iot-auth.md"),
]

def setup_db(bardic_knowledge: bool):
    temp_dir = tempfile.mkdtemp(prefix=f"discrimination_test_{bardic_knowledge}_")
    settings = Settings.from_env()
    settings.chroma_path = temp_dir
    settings.bardic_knowledge = bardic_knowledge
    
    store = ChromaVectorStore(settings)
    processor = DocumentProcessor(settings)
    
    docs_dir = Path(__file__).parent / "fixtures" / "discrimination_docs"
    for doc_path in docs_dir.glob("*.md"):
        chunks = processor.process(doc_path)
        store.add_documents(chunks)
        
    return store, temp_dir

def test_discrimination_with_and_without_prefixing():
    print("\n\n=== DISCRIMINATION TEST (Structural Integrity Audit) ===")
    
    # 1. Test WITH Bardic Knowledge
    print("\n--- Path: WITH Bardic Knowledge (Prefixing) ---")
    store_on, dir_on = setup_db(True)
    results_on = []
    try:
        for query, expected_file in QUERIES:
            search_results = search_with_routing(store_on, query, n_results=3)
            top_result = search_results[0] if search_results else None
            top_file = Path(top_result.metadata['source']).name if top_result else "NONE"
            success = top_file == expected_file
            
            # Calculate gap between result 1 and 2
            gap = 0
            if len(search_results) > 1:
                gap = search_results[0].score - search_results[1].score
                
            print(f"Q: {query:40} | Top: {top_file:15} | Success: {str(success):5} | Gap: {gap:.4f}")
            results_on.append((success, gap))
    finally:
        shutil.rmtree(dir_on)
        
    # 2. Test WITHOUT Bardic Knowledge
    print("\n--- Path: WITHOUT Bardic Knowledge (Naked) ---")
    store_off, dir_off = setup_db(False)
    results_off = []
    try:
        for query, expected_file in QUERIES:
            search_results = search_with_routing(store_off, query, n_results=3)
            top_result = search_results[0] if search_results else None
            top_file = Path(top_result.metadata['source']).name if top_result else "NONE"
            success = top_file == expected_file
            
            # Calculate gap between result 1 and 2
            gap = 0
            if len(search_results) > 1:
                gap = search_results[0].score - search_results[1].score
                
            print(f"Q: {query:40} | Top: {top_file:15} | Success: {str(success):5} | Gap: {gap:.4f}")
            results_off.append((success, gap))
    finally:
        shutil.rmtree(dir_off)
        
    # Summary
    success_on = sum(1 for s, g in results_on if s)
    success_off = sum(1 for s, g in results_off if s)
    avg_gap_on = sum(g for s, g in results_on) / len(results_on)
    avg_gap_off = sum(g for s, g in results_off) / len(results_off)
    
    print(f"\nSummary:")
    print(f"  Prefixing ON : Success {success_on}/{len(QUERIES)}, Avg Gap {avg_gap_on:.4f}")
    print(f"  Prefixing OFF: Success {success_off}/{len(QUERIES)}, Avg Gap {avg_gap_off:.4f}")
    
    # We expect prefixing to at least maintain or improve success and gap
    assert success_on >= success_off
