import json
from pathlib import Path

def load_results(path):
    with open(path) as f:
        return json.load(f)

def render_bar(val, length=20):
    filled = int(val * length)
    return "█" * filled + "░" * (length - filled)

def visualize():
    simple = load_results("tests/results/router_simple_benchmark.json")
    precise = load_results("tests/results/router_precise_benchmark.json")
    
    difficulties = ["easy", "medium", "hard"]
    
    print("\n" + "="*60)
    print("      CANDLEKEEP RETRIEVAL QUALITY VISUALIZATION")
    print("="*60)
    
    print("\nPRECISION BY DIFFICULTY")
    print("-" * 30)
    for diff in difficulties:
        s_p = simple["summary"]["by_difficulty"][diff]["precision"]
        p_p = precise["summary"]["by_difficulty"][diff]["precision"]
        
        print(f"{diff.upper():8} Simple:  {s_p:6.1%} {render_bar(s_p)}")
        print(f"{' ':8} Precise: {p_p:6.1%} {render_bar(p_p)}")
        print()

    print("RECALL BY DIFFICULTY")
    print("-" * 30)
    for diff in difficulties:
        s_r = simple["summary"]["by_difficulty"][diff]["recall"]
        p_r = precise["summary"]["by_difficulty"][diff]["recall"]
        
        print(f"{diff.upper():8} Simple:  {s_r:6.1%} {render_bar(min(s_r, 1.0))}")
        print(f"{' ':8} Precise: {p_r:6.1%} {render_bar(min(p_r, 1.0))}")
        print()

    print("LATENCY (ms) - CPU Baseline")
    print("-" * 30)
    for diff in difficulties:
        s_l = simple["summary"]["by_difficulty"][diff]["latency_ms"]
        p_l = precise["summary"]["by_difficulty"][diff]["latency_ms"]
        
        def log_bar(ms, max_ms=1000):
            val = min(ms / max_ms, 1.0)
            return "█" * int(val * 20)

        print(f"{diff.upper():8} Simple:  {s_l:6.0f}ms {log_bar(s_l)}")
        print(f"{' ':8} Precise: {p_l:6.0f}ms {log_bar(p_l)}")
        print()

    print("="*60)

if __name__ == "__main__":
    visualize()
