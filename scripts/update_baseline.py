
import shutil
from pathlib import Path

def main():
    results_dir = Path("tests/results")
    archive_dir = Path("tests/results/archive")
    
    # Ensure directories exist
    if not results_dir.exists():
        print(f"Error: Results directory {results_dir} not found.")
        return
    
    archive_dir.mkdir(parents=True, exist_ok=True)
    
    # Files to promote
    paths = ["simple", "hybrid", "precise"]
    updated = []
    
    for path in paths:
        src = results_dir / f"router_{path}_benchmark.json"
        dst = archive_dir / f"router_{path}_benchmark.json"
        
        if src.exists():
            print(f"Promoting {src} -> {dst}")
            shutil.copy2(src, dst)
            updated.append(path)
        else:
            print(f"Warning: {src} not found, skipping.")
            
    if updated:
        print(f"\n✅ Successfully updated baselines for: {', '.join(updated)}")
    else:
        print("\n⚠️ No benchmark files found to update.")

if __name__ == "__main__":
    main()
