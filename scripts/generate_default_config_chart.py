#!/usr/bin/env python3
"""Generate radar chart for the default-config competitive benchmark.

Reads tests/results/default_config_benchmark.json and produces
docs/default_config_radar.png for embedding in the research diary.

Usage:
    python scripts/generate_default_config_chart.py
"""
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path


def main():
    results_path = Path("tests/results/default_config_benchmark.json")
    data = json.loads(results_path.read_text())
    summaries = data["summaries"]

    lc = summaries["langchain-defaults"]
    ck = summaries["candlekeep-hybrid"]

    # gNDCG values from benchmark output (not stored in summaries by
    # the generic summarizer — read from the raw output)
    lc_gndcg = 0.2159
    ck_gndcg = 0.4217

    labels = ["MRR", "gNDCG@5", "Content\nMatch", "HR@5", "Precision@5"]
    lc_vals = [lc["mrr"], lc_gndcg, lc.get("content_match", 0), lc["hit_rate_5"], lc["precision_5"]]
    ck_vals = [ck["mrr"], ck_gndcg, ck.get("content_match", 0), ck["hit_rate_5"], ck["precision_5"]]

    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    lc_vals += lc_vals[:1]
    ck_vals += ck_vals[:1]
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))
    fig.patch.set_facecolor("white")

    ax.plot(angles, lc_vals, "o-", linewidth=2, color="#e74c3c",
            label="LangChain defaults", markersize=6)
    ax.fill(angles, lc_vals, alpha=0.12, color="#e74c3c")

    ax.plot(angles, ck_vals, "s-", linewidth=2, color="#2980b9",
            label="Candlekeep hybrid", markersize=6)
    ax.fill(angles, ck_vals, alpha=0.12, color="#2980b9")

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=12, fontweight="bold")
    ax.set_ylim(0, 1.0)
    ax.set_yticks([0.2, 0.4, 0.6, 0.8])
    ax.set_yticklabels(["0.2", "0.4", "0.6", "0.8"], fontsize=9, color="#666")
    ax.yaxis.grid(True, color="#ddd", linewidth=0.8)
    ax.xaxis.grid(True, color="#ccc", linewidth=0.8)

    for angle, lc_v, ck_v in zip(angles[:-1], lc_vals[:-1], ck_vals[:-1]):
        offset = 0.06
        ax.text(angle, lc_v + offset, f"{lc_v:.3f}", ha="center", va="bottom",
                fontsize=8, color="#c0392b", fontweight="bold")
        ax.text(angle, ck_v - offset, f"{ck_v:.3f}", ha="center", va="top",
                fontsize=8, color="#2471a3", fontweight="bold")

    ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.12), fontsize=11,
              framealpha=0.9)
    ax.set_title(
        "Out-of-the-Box: LangChain vs Candlekeep\n"
        "(Centurion Set, 108 queries, 3 runs)",
        fontsize=13, fontweight="bold", pad=25,
    )
    fig.text(
        0.5, 0.02,
        "LangChain: mpnet-base-v2 (109M), 1000/200 chunks  |  "
        "Candlekeep: bge-small (33M), hybrid path",
        ha="center", fontsize=9, color="#888",
    )

    out_path = Path("docs/charts/langchain-vs-candlekeep-out-of-the-box.png")
    plt.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="white")
    print(f"Saved to {out_path}")


if __name__ == "__main__":
    main()
