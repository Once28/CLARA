"""
Generate retrieval evaluation plots from a CSV file produced by evaluate_retrieval.py.

Usage:
    python test/plot_results.py
    python test/plot_results.py --csv test/results/retrieval_results.csv --out test/results/retrieval_curves.png
"""

import csv
from pathlib import Path
from collections import defaultdict


def load_csv(csv_path: Path) -> dict:
    """
    Returns nested dict: data[model][k] = {metric: mean, metric_std: std, ...}
    """
    data = defaultdict(dict)
    with open(csv_path, newline="") as f:
        for row in csv.DictReader(f):
            model = row["model"]
            k = int(row["k"])
            data[model][k] = {col: float(val) for col, val in row.items() if col not in ("model", "k")}
    return data


def plot(data: dict, output_path: Path):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.ticker as ticker
    except ImportError:
        print("matplotlib not installed — run: pip install matplotlib")
        return

    models = sorted(data.keys())
    k_sorted = sorted(next(iter(data.values())).keys())

    _palette = ["#e94560", "#0f3460", "#2ec4b6", "#ff9f1c", "#533483", "#44cf6c", "#f4a261", "#adb5bd"]
    model_colors = {m: _palette[i % len(_palette)] for i, m in enumerate(models)}

    fig, axes = plt.subplots(2, 3, figsize=(16, 9))
    fig.suptitle("CLARA Retrieval Evaluation — Embedding Model Comparison",
                 fontsize=13, fontweight="bold")

    k_panels = [
        ("Recall@k",    "Recall@k",    False, axes[0, 0]),
        ("Precision@k", "Precision@k", False, axes[0, 1]),
        ("HitRate",     "Hit Rate@k",  False, axes[0, 2]),
        ("NDCG@k",      "NDCG@k",      False, axes[1, 0]),
        ("MRR",         "MRR@k",       False, axes[1, 1]),
        ("MAP",         "MAP@k",       False, axes[1, 2]),
    ]
    for col, label, primary, ax in k_panels:
        std_col = f"{col}_std"
        for model in models:
            y   = [data[model][k][col]     for k in k_sorted]
            err = [data[model][k][std_col] for k in k_sorted]
            lo  = [max(0.0, v - e/2) for v, e in zip(y, err)]
            hi  = [min(1.0, v + e/2) for v, e in zip(y, err)]
            ax.plot(k_sorted, y,
                    marker="o", markersize=4,
                    linewidth=2.5 if primary else 1.8,
                    label=model, color=model_colors[model])
            ax.fill_between(k_sorted, lo, hi, alpha=0.12, color=model_colors[model])

        ax.set_xlabel("k-chunks retrieved", fontsize=9)
        ax.set_ylabel(label, fontsize=9)
        title = f"{label}  \u2b50" if primary else label
        ax.set_title(title, fontsize=10, fontweight="bold" if primary else "normal")
        ax.set_ylim(0, 1.08)
        ax.legend(fontsize=8, framealpha=0.85)
        ax.grid(True, alpha=0.3)
        ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Plot saved to {output_path}")

import numpy as np

# CSV model name → display name (must match values in the 'model' column)
MODEL_NAME_MAP = {
    "embeddinggemma": "EmbeddingGemma",
    "medsiglip":      "MedSigLIP",
    "minilm":         "MiniLM",
    "random":         "Random",
}

K_VALUES = [5, 10, 15, 20]

METRICS = [
    ("Recall@k",    "Recall"),
    ("Precision@k", "Precision"),
    ("MRR",         "MRR"),
    ("NDCG@k",      "NDCG"),
    ("MAP",         "MAP"),
    ("HitRate",     "Hit Rate"),
]


def build_markdown_table(data: dict, k: int) -> str:
    """Build a markdown table for a given k from the nested data dict."""
    models_ordered = [m for m in MODEL_NAME_MAP if m in data]
    display_names = [MODEL_NAME_MAP[m] for m in models_ordered]

    header = "| Metric | " + " | ".join(f"**{d}**" for d in display_names) + " |\n"
    header += "|---|" + "|".join("---" for _ in models_ordered) + "|\n"

    rows = ""
    for metric_col, metric_name in METRICS:
        raw_values = [data[m][k].get(metric_col, float("nan")) for m in models_ordered]
        best = max((v for v in raw_values if not np.isnan(v)), default=float("nan"))

        cells = []
        for v in raw_values:
            if np.isnan(v):
                cells.append("")
            else:
                fmt = f"{v:.4f}"
                cells.append(f"**{fmt}**" if v == best else fmt)

        rows += f"| **{metric_name}@k={k}** | " + " | ".join(cells) + " |\n"

    return header + rows


def main():
    csv_path = Path("test/results/retrieval_results.csv")
    if not csv_path.exists():
        print(f"CSV not found: {csv_path}")
        print("Run evaluate_retrieval.py first to generate it.")
        raise SystemExit(1)

    data = load_csv(csv_path)
    print(f"Loaded results for {len(data)} models from {csv_path}")

    plot(data, Path("test/results/retrieval_curves.png"))

    for k in K_VALUES:
        print(f"\n## Results @ k = {k}\n")
        print(build_markdown_table(data, k))


main()
