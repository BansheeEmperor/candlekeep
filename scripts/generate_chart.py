import json
from pathlib import Path

def load_results(path):
    with open(path) as f:
        return json.load(f)

def generate_html():
    simple = load_results("tests/results/router_simple_benchmark.json")
    precise = load_results("tests/results/router_precise_benchmark.json")
    
    difficulties = ["easy", "medium", "hard"]
    
    data = {
        "labels": [d.upper() for d in difficulties],
        "precision": {
            "hybrid": [simple["summary"]["by_difficulty"][d]["precision"] * 100 for d in difficulties],
            "precise": [precise["summary"]["by_difficulty"][d]["precision"] * 100 for d in difficulties]
        },
        "recall": {
            "hybrid": [simple["summary"]["by_difficulty"][d]["recall"] * 100 for d in difficulties],
            "precise": [precise["summary"]["by_difficulty"][d]["recall"] * 100 for d in difficulties]
        },
        "latency": {
            "hybrid": [simple["summary"]["by_difficulty"][d]["latency_ms"] for d in difficulties],
            "precise": [precise["summary"]["by_difficulty"][d]["latency_ms"] for d in difficulties]
        }
    }

    html_template = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Candlekeep Benchmark Results</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: sans-serif; margin: 40px; background: #f4f4f9; }}
        .container {{ max-width: 1000px; margin: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ text-align: center; color: #333; }}
        .definitions {{ 
            background: #eef2f7; 
            padding: 15px; 
            border-radius: 6px; 
            margin-bottom: 30px; 
            border-left: 5px solid #36a2eb;
            font-size: 0.95em;
        }}
        .definitions p {{ margin: 5px 0; }}
        .chart-container {{ position: relative; margin: auto; height: 400px; width: 100%; margin-bottom: 50px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Candlekeep RAG Benchmarks</h1>
        
        <div class="definitions">
            <p><strong>Precision:</strong> Percentage of retrieved chunks that belong to relevant documents. (How "clean" are the results?)</p>
            <p><strong>Recall:</strong> Percentage of expected documents found. (Did we find everything we were looking for?)</p>
        </div>

        <div class="chart-container">
            <canvas id="precisionChart"></canvas>
        </div>
        
        <div class="chart-container">
            <canvas id="recallChart"></canvas>
        </div>

        <div class="chart-container">
            <canvas id="latencyChart"></canvas>
        </div>
    </div>

    <script>
        const labels = {json.dumps(data['labels'])};
        
        const createChart = (id, title, simpleData, preciseData, unit) => {{
            new Chart(document.getElementById(id), {{
                type: 'bar',
                data: {{
                    labels: labels,
                    datasets: [
                        {{
                            label: 'Simple Path',
                            data: simpleData,
                            backgroundColor: 'rgba(54, 162, 235, 0.6)',
                            borderColor: 'rgba(54, 162, 235, 1)',
                            borderWidth: 1
                        }},
                        {{
                            label: 'Precise Path',
                            data: preciseData,
                            backgroundColor: 'rgba(255, 99, 132, 0.6)',
                            borderColor: 'rgba(255, 99, 132, 1)',
                            borderWidth: 1
                        }}
                    ]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        title: {{ display: true, text: title, font: {{ size: 18 }} }}
                    }},
                    scales: {{
                        y: {{ beginAtZero: true, title: {{ display: true, text: unit }} }}
                    }}
                }}
            }});
        }};

        createChart('precisionChart', 'Precision by Difficulty', {json.dumps(data['precision']['simple'])}, {json.dumps(data['precision']['precise'])}, 'Percentage (%)');
        createChart('recallChart', 'Recall by Difficulty', {json.dumps(data['recall']['simple'])}, {json.dumps(data['recall']['precise'])}, 'Percentage (%)');
        createChart('latencyChart', 'Latency (CPU Baseline)', {json.dumps(data['latency']['simple'])}, {json.dumps(data['latency']['precise'])}, 'Milliseconds (ms)');
    </script>
</body>
</html>
"""
    
    output_path = Path("docs/benchmark_chart.html")
    output_path.write_text(html_template)
    print(f"📊 Graphical chart generated at: {output_path}")

if __name__ == "__main__":
    generate_html()
