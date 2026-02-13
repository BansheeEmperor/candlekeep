#!/usr/bin/env python3
"""Run baseline benchmark - wrapper for pytest."""
import sys
import subprocess
from pathlib import Path

def main():
    """Run benchmark via pytest."""
    test_file = Path(__file__).parent.parent / "tests" / "test_benchmark.py"
    
    # Run pytest with verbose output
    result = subprocess.run(
        ["pytest", str(test_file), "-v", "-s", "--tb=short"],
        cwd=Path(__file__).parent.parent
    )
    
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
