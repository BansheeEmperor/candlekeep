
import json
import sys
from pathlib import Path

def load_json(path):
    if not Path(path).exists():
        return None
    with open(path, 'r') as f:
        return json.load(f)

def get_significance(new, old, metric_type):
    if old == 0:
        return "🟢 New" if new > 0 else ""
    
    delta = new - old
    if metric_type == "precision":
        if delta > 0.01: return f"🟢 +{delta:.1%}"
        if delta < -0.01: return f"🔴 {delta:.1%}"
    elif metric_type == "latency":
        # Latency is noisy, 15% threshold for significance
        percent_change = (delta / old)
        if percent_change < -0.15: return f"⚡ {percent_change:.1%}"
        if percent_change > 0.15: return f"⚠️ +{percent_change:.1%}"
    return "−"

def main():
    if len(sys.argv) < 3:
        print("Usage: compare_benchmarks.py <baseline_json> <new_results_json>")
        sys.exit(1)

    baseline = load_json(sys.argv[1])
    current = load_json(sys.argv[2])

    if not current:
        print("Error: New results not found")
        sys.exit(1)

    # Use a dummy baseline if missing to avoid crashing
    if not baseline:
        baseline = {"summary": {"avg_precision": 0, "avg_recall": 0, "avg_latency_ms": 0}}

    b_sum = baseline["summary"]
    c_sum = current["summary"]

    print("### 📊 Benchmark Comparison")
    print("")
    print("| Metric | Baseline | Current | Change |")
    print("| :--- | :--- | :--- | :--- |")
    
    metrics = [
        ("Avg Precision", "avg_precision", "precision"),
        ("Avg Recall", "avg_recall", "precision"),
        ("Avg Latency", "avg_latency_ms", "latency"),
    ]

    for label, key, m_type in metrics:
        b_val = b_sum.get(key, 0)
        c_val = c_sum.get(key, 0)
        
        sig = get_significance(c_val, b_val, m_type)
        
        if m_type == "precision":
            b_str = f"{b_val:.1%}"
            c_str = f"{c_val:.1%}"
        else:
            b_str = f"{b_val:.0f}ms"
            c_str = f"{c_val:.0f}ms"
            
        print(f"| {label} | {b_str} | {c_str} | {sig} |")

if __name__ == "__main__":
    main()
