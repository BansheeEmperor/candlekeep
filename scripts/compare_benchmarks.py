
import json
import sys
from pathlib import Path

def load_json(path):
    if not Path(path).exists():
        return None
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except:
        return None

def get_significance(new, old, metric_type):
    if old == 0:
        return "🟢 New" if new > 0 else "−"
    
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
    # Expected args: <label1> <base1> <new1> ...
    args = sys.argv[1:]
    if len(args) < 3 or len(args) % 3 != 0:
        print("Usage: compare_benchmarks.py <label> <base> <new> [...]")
        sys.exit(1)

    print("### 📊 Performance Comparison")
    print("")
    print("<table>")
    print("  <thead>")
    print("    <tr>")
    print("      <th align='left'>Metric</th>")
    print("      <th align='right'>Baseline</th>")
    print("      <th align='right'>Current</th>")
    print("      <th align='center'>Change</th>")
    print("    </tr>")
    print("  </thead>")
    print("  <tbody>")
    
    # Define colors for labels
    label_colors = {
        "Simple Path": "🟢",
        "Hybrid Path": "🧬",
        "Precise Path": "🎯"
    }

    for i in range(0, len(args), 3):
        full_label = args[i]
        baseline = load_json(args[i+1])
        current = load_json(args[i+2])
        
        if not current:
            continue

        if not baseline:
            baseline = {"summary": {"avg_precision": 0, "avg_recall": 0, "avg_latency_ms": 0}}

        color = "⚪"
        for key in label_colors:
            if key in full_label:
                color = label_colors[key]
                break

        # Divider Row using colspan for consolidation
        print(f"    <tr style='background-color: #f6f8fa;'>")
        print(f"      <td colspan='4'><strong>{color} {full_label}</strong></td>")
        print(f"    </tr>")
        
        b_sum = baseline["summary"]
        c_sum = current["summary"]
        
        metrics = [
            ("Avg Precision", "avg_precision", "precision"),
            ("Avg Recall", "avg_recall", "precision"),
            ("Avg Latency", "avg_latency_ms", "latency"),
        ]

        for m_label, key, m_type in metrics:
            b_val = b_sum.get(key, 0)
            c_val = c_sum.get(key, 0)
            
            sig = get_significance(c_val, b_val, m_type)
            
            if m_type == "precision":
                b_str = f"{b_val:.1%}"
                c_str = f"{c_val:.1%}"
            else:
                b_str = f"{b_val:.0f}ms"
                c_str = f"{c_val:.0f}ms"
                
            print(f"    <tr>")
            print(f"      <td>&nbsp;&nbsp;{m_label}</td>")
            print(f"      <td align='right'>{b_str}</td>")
            print(f"      <td align='right'>{c_str}</td>")
            print(f"      <td align='center'>{sig}</td>")
            print(f"    </tr>")

    print("  </tbody>")
    print("</table>")

if __name__ == "__main__":
    main()
