#!/usr/bin/env python3
import sys
import traceback
from pathlib import Path

def download():
    try:
        from candlekeep.config import Settings, EMBEDDING_MODELS
        from sentence_transformers import SentenceTransformer, CrossEncoder
        
        settings = Settings.from_env()
        models_dir = settings.models_dir
        models_dir.mkdir(parents=True, exist_ok=True)
        
        model_id = EMBEDDING_MODELS[settings.embedding_model]
        print(f"Downloading Bi-Encoder: {model_id} into {models_dir}")
        SentenceTransformer(model_id, cache_folder=str(models_dir))
        
        print(f"Downloading Cross-Encoder: ms-marco-MiniLM-L-6-v2 into {models_dir}")
        CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2", cache_folder=str(models_dir))
        
        print("✓ All models downloaded successfully")
    except Exception as e:
        print(f"❌ Error downloading models: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    download()
