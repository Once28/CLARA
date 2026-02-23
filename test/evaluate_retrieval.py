"""
Evaluate retrieval quality across CLARA's three embedding strategies.

Compares MedSigLIP, all-MiniLM-L6-v2, and EmbeddingGemma 300M on:
  - Recall@k    (priority metric — missing a regulation is costly)
  - Precision@k
  - MRR         (Mean Reciprocal Rank — how early the first relevant chunk appears)
  - NDCG@k      (Normalized Discounted Cumulative Gain — rank-aware relevance)
  - MAP         (Mean Average Precision)
  - Hit Rate    (% of queries with at least one relevant result in top-k)

Architecture:
  For each (protocol, regulation) pair in the ground truth:
    1. Index the protocol chunks using each embedding model
    2. Use the regulation text as the query (reversed RAG, matching server.py)
    3. Compare retrieved chunk indices against ground-truth relevant indices
    4. Compute metrics

Usage:
    # Run with synthetic ground truth only (no external dependencies)
    python test/evaluate_retrieval.py --ground-truth test/ground_truth/annotations_full.json

    # Compare specific models
    python test/evaluate_retrieval.py --models minilm medsiglip

    # Adjust retrieval depth
    python test/evaluate_retrieval.py --k 3 5 10

    # Generate HTML report
    python test/evaluate_retrieval.py --report test/results/retrieval_report.html
"""

import csv
import json
import math
import os
import sys
import time
import logging
import argparse
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

import numpy as np

# Load .env from the project root (one level up from test/)
_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(_env_path)
    except ImportError:
        pass  # python-dotenv not installed; env vars must be set in the shell

logger = logging.getLogger("clara.eval")

# ─── Metric implementations ──────────────────────────────────

def recall_at_k(retrieved_indices: list[int], relevant_indices: list[int], k: int) -> float:
    """Fraction of relevant items that appear in the top-k retrieved."""
    if not relevant_indices:
        return 1.0  # vacuously true — nothing to miss
    retrieved_set = set(retrieved_indices[:k])
    hits = sum(1 for idx in relevant_indices if idx in retrieved_set)
    return hits / len(relevant_indices)


def precision_at_k(retrieved_indices: list[int], relevant_indices: list[int], k: int) -> float:
    """Fraction of top-k retrieved items that are relevant."""
    if k == 0:
        return 0.0
    retrieved_set = set(retrieved_indices[:k])
    relevant_set = set(relevant_indices)
    hits = len(retrieved_set & relevant_set)
    return hits / k


def mean_reciprocal_rank(retrieved_indices: list[int], relevant_indices: list[int]) -> float:
    """1 / (rank of first relevant result). 0 if no relevant result found."""
    relevant_set = set(relevant_indices)
    for rank, idx in enumerate(retrieved_indices, start=1):
        if idx in relevant_set:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(
    retrieved_indices: list[int],
    relevant_indices: list[int],
    relevance_scores: list[int],
    k: int,
) -> float:
    """
    Normalized Discounted Cumulative Gain.
    relevance_scores[i] corresponds to relevant_indices[i].
    """
    if not relevant_indices:
        return 1.0

    # Build relevance lookup: chunk_index -> score
    rel_map = dict(zip(relevant_indices, relevance_scores))

    # DCG of retrieved
    dcg = 0.0
    for rank, idx in enumerate(retrieved_indices[:k], start=1):
        rel = rel_map.get(idx, 0)
        dcg += (2 ** rel - 1) / math.log2(rank + 1)

    # Ideal DCG: sort all relevance scores descending
    ideal_scores = sorted(relevance_scores, reverse=True)[:k]
    idcg = sum((2 ** s - 1) / math.log2(rank + 1) for rank, s in enumerate(ideal_scores, start=1))

    return dcg / idcg if idcg > 0 else 0.0


def average_precision(retrieved_indices: list[int], relevant_indices: list[int]) -> float:
    """Average precision for a single query."""
    if not relevant_indices:
        return 1.0
    relevant_set = set(relevant_indices)
    hits = 0
    sum_precision = 0.0
    for rank, idx in enumerate(retrieved_indices, start=1):
        if idx in relevant_set:
            hits += 1
            sum_precision += hits / rank
    return sum_precision / len(relevant_indices)


def hit_rate_at_k(retrieved_indices: list[int], relevant_indices: list[int], k: int) -> float:
    """1 if at least one relevant item in top-k, else 0."""
    if not relevant_indices:
        return 1.0
    retrieved_set = set(retrieved_indices[:k])
    return 1.0 if any(idx in retrieved_set for idx in relevant_indices) else 0.0


# ─── Embedding strategy wrappers ──────────────────────────────

@dataclass
class RetrievalResult:
    model_name: str
    protocol_id: str
    regulation: str
    retrieved_indices: list[int]
    query_time_ms: float


class EmbeddingEvaluator:
    """
    Wraps each embedding strategy to produce chunk rankings.
    Falls back to random baseline if the model is unavailable.
    """

    def __init__(self, model_name: str):
        self.model_name = model_name
        self._embeddings = None
        self._available = None

    def is_available(self) -> bool:
        if self._available is not None:
            return self._available
        try:
            self._embeddings = self._load_embeddings()
            self._available = True
        except Exception as e:
            logger.warning("Model '%s' not available: %s", self.model_name, e)
            self._available = False
        return self._available

    def _load_embeddings(self):
        if self.model_name == "minilm":
            from langchain_huggingface import HuggingFaceEmbeddings
            return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        elif self.model_name == "medsiglip":
            sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
            if os.environ.get("MEDSIGLIP_ENDPOINT_ID", "").strip():
                # Model Garden Vertex endpoint takes priority
                from vector_store import MedSigLIPVertexEmbeddings
                return MedSigLIPVertexEmbeddings()
            else:
                # HuggingFace path: tries real checkpoint, falls back to SigLIP proxy
                from vector_store import MedSigLIPTextEmbeddings
                return MedSigLIPTextEmbeddings()
        elif self.model_name == "embeddinggemma":
            return self._load_embeddinggemma()
        elif self.model_name == "random":
            return None  # random baseline
        else:
            raise ValueError(f"Unknown model: {self.model_name}")

    def _load_embeddinggemma(self):
        """
        Load EmbeddingGemma via Vertex AI.

        If EMBEDDINGGEMMA_ENDPOINT_ID is set, calls the Model Garden custom
        endpoint directly. Otherwise uses the managed text-embedding-005 API.
        Both require GCP_PROJECT_ID and gcloud auth application-default login.
        """
        from google.cloud import aiplatform
        from langchain_core.embeddings import Embeddings

        project = os.environ.get("GCP_PROJECT_ID", "")
        endpoint_id = os.environ.get("EMBEDDINGGEMMA_ENDPOINT_ID", "").strip()
        # Use endpoint-specific region (may differ from the MedGemma GCP_REGION)
        region = os.environ.get("EMBEDDINGGEMMA_ENDPOINT_REGION") or os.environ.get("GCP_REGION", "europe-west4")

        if not project:
            raise ValueError("GCP_PROJECT_ID not set — cannot use EmbeddingGemma")

        aiplatform.init(project=project, location=region)

        if endpoint_id:
            # Model Garden custom endpoint — full resource name routes to the correct region
            resource_name = f"projects/{project}/locations/{region}/endpoints/{endpoint_id}"
            endpoint = aiplatform.Endpoint(resource_name)
            logger.info("EmbeddingGemma using Model Garden endpoint: %s (%s)", endpoint_id, region)

            class EmbeddingGemmaVertexEmbeddings(Embeddings):
                def __init__(self, ep):
                    self._endpoint = ep

                @staticmethod
                def _extract_vector(pred) -> list[float]:
                    # EmbeddingGemma returns [[float, ...]] — unwrap the outer list
                    if isinstance(pred, list):
                        if len(pred) == 1 and isinstance(pred[0], list):
                            return pred[0]
                        return pred
                    if isinstance(pred, dict):
                        for key in ("embeddings", "embedding", "values", "vector"):
                            val = pred.get(key)
                            if isinstance(val, dict):
                                val = val.get("values") or val.get("vector")
                            if isinstance(val, list):
                                return val
                    raise ValueError(f"Unrecognised prediction shape: {type(pred)}")

                def embed_documents(self, texts: list[str]) -> list[list[float]]:
                    batch_size = 16  # conservative to stay under payload limits
                    all_embeddings: list[list[float]] = []
                    for i in range(0, len(texts), batch_size):
                        batch = texts[i : i + batch_size]
                        instances = [{"inputs": t} for t in batch]
                        response = self._endpoint.predict(instances=instances)
                        all_embeddings.extend(
                            self._extract_vector(p) for p in response.predictions
                        )
                    return all_embeddings

                def embed_query(self, text: str) -> list[float]:
                    return self.embed_documents([text])[0]

            return EmbeddingGemmaVertexEmbeddings(endpoint)
        else:
            # Managed text-embedding-005 API
            logger.info("EmbeddingGemma using managed text-embedding-005 API")

            class EmbeddingGemmaManagedEmbeddings(Embeddings):
                def __init__(self):
                    from vertexai.language_models import TextEmbeddingModel
                    self.model = TextEmbeddingModel.from_pretrained("text-embedding-005")

                def embed_documents(self, texts: list[str]) -> list[list[float]]:
                    return [e.values for e in self.model.get_embeddings(texts)]

                def embed_query(self, text: str) -> list[float]:
                    return self.embed_documents([text])[0]

            return EmbeddingGemmaManagedEmbeddings()

    def retrieve(
        self,
        chunks: list[str],
        query: str,
        k: int = 10,
    ) -> RetrievalResult:
        """
        Embed chunks + query, rank by cosine similarity, return top-k indices.
        """
        start = time.time()

        if self.model_name == "random" or not self.is_available():
            # Random baseline
            indices = list(np.random.permutation(len(chunks))[:k].tolist())
            elapsed = (time.time() - start) * 1000
            return RetrievalResult(
                model_name=self.model_name,
                protocol_id="",
                regulation="",
                retrieved_indices=indices,
                query_time_ms=elapsed,
            )

        # Embed
        chunk_embeddings = np.array(self._embeddings.embed_documents(chunks))
        query_embedding = np.array(self._embeddings.embed_query(query))

        # Cosine similarity (embeddings should already be normalized for most models)
        norms_c = np.linalg.norm(chunk_embeddings, axis=1, keepdims=True)
        norms_c = np.where(norms_c == 0, 1, norms_c)
        chunk_embeddings_norm = chunk_embeddings / norms_c

        norm_q = np.linalg.norm(query_embedding)
        norm_q = 1 if norm_q == 0 else norm_q
        query_embedding_norm = query_embedding / norm_q

        similarities = chunk_embeddings_norm @ query_embedding_norm
        top_k_indices = np.argsort(similarities)[::-1][:k].tolist()

        elapsed = (time.time() - start) * 1000

        return RetrievalResult(
            model_name=self.model_name,
            protocol_id="",
            regulation="",
            retrieved_indices=top_k_indices,
            query_time_ms=elapsed,
        )


# ─── Regulation query text ────────────────────────────────────
# Shortened representative queries per regulation, simulating what the eCFR
# text would look like when used as a retrieval query.

REGULATION_QUERIES = {
    "21 CFR Part 11": (
        "Electronic records electronic signatures. Persons who use closed systems to create, "
        "modify, maintain, or transmit electronic records shall employ procedures and controls "
        "designed to ensure the authenticity, integrity, and confidentiality of electronic records. "
        "Audit trails, system validation, authority checks, device checks."
    ),
    "21 CFR Part 50": (
        "Protection of human subjects. Informed consent of human subjects. No investigator may "
        "involve a human being as a subject in research unless the investigator has obtained the "
        "legally effective informed consent of the subject or the subject's legally authorized "
        "representative. Elements of informed consent: risks, benefits, alternatives, "
        "confidentiality, compensation for injury, voluntary participation."
    ),
    "21 CFR Part 56": (
        "Institutional Review Boards. An IRB shall review and have authority to approve, require "
        "modifications, or disapprove all research activities. IRB membership, functions and "
        "operations, review of research, record keeping, continuing review."
    ),
    "21 CFR Part 58": (
        "Good Laboratory Practice for nonclinical laboratory studies. Organization and personnel, "
        "testing facilities, equipment, testing facilities operation, test and control articles, "
        "protocol and conduct of a nonclinical laboratory study, quality assurance unit."
    ),
    "21 CFR Part 211": (
        "Current good manufacturing practice for finished pharmaceuticals. Organization and "
        "personnel, buildings and facilities, equipment, production and process controls, "
        "packaging and labeling, holding and distribution, laboratory controls, records and reports."
    ),
    "21 CFR Part 312": (
        "Investigational new drug application. IND content and format, IND safety reporting, "
        "responsibilities of sponsors and investigators, safety reports, annual reports, "
        "protocol amendments, information amendments, clinical holds."
    ),
    "21 CFR Part 314": (
        "Applications for FDA approval to market a new drug. New drug application content and "
        "format, NDA review and action, supplements and other changes, postmarketing reports."
    ),
    "45 CFR Part 46": (
        "Protection of human subjects. Federal Policy for the Protection of Human Subjects "
        "(Common Rule). Definitions, IRB review, informed consent, additional protections for "
        "pregnant women, prisoners, children. Federal-wide assurance, OHRP oversight."
    ),
}


# ─── Main evaluation loop ────────────────────────────────────

@dataclass
class EvalMetrics:
    """Aggregated metrics for one (model, k) combination."""
    model: str
    k: int
    recall: list[float] = field(default_factory=list)
    precision: list[float] = field(default_factory=list)
    mrr: list[float] = field(default_factory=list)
    ndcg: list[float] = field(default_factory=list)
    ap: list[float] = field(default_factory=list)
    hit_rate: list[float] = field(default_factory=list)
    query_times_ms: list[float] = field(default_factory=list)

    def mean(self, attr: str) -> float:
        vals = getattr(self, attr)
        return float(np.mean(vals)) if vals else 0.0

    def std(self, attr: str) -> float:
        vals = getattr(self, attr)
        return float(np.std(vals)) if vals else 0.0


def run_evaluation(
    ground_truth_path: Path,
    model_names: list[str],
    k_values: list[int],
    report_path: Optional[Path] = None,
    max_samples: Optional[int] = None,
    plot_path: Optional[Path] = None,
    csv_path: Optional[Path] = None,
) -> dict:
    """
    Main evaluation driver.

    Returns nested dict: results[model_name][k] = EvalMetrics
    """
    # Load ground truth
    with open(ground_truth_path) as f:
        samples = json.load(f)

    if max_samples:
        samples = samples[:max_samples]

    logger.info("Loaded %d ground truth samples", len(samples))

    # Initialize evaluators
    evaluators = {}
    for name in model_names:
        ev = EmbeddingEvaluator(name)
        if ev.is_available() or name == "random":
            evaluators[name] = ev
            logger.info("✓ Model '%s' loaded", name)
        else:
            logger.warning("✗ Model '%s' unavailable — skipping", name)

    if not evaluators:
        logger.error("No models available. Exiting.")
        return {}

    # Results storage
    results: dict[str, dict[int, EvalMetrics]] = {}
    for model_name in evaluators:
        results[model_name] = {k: EvalMetrics(model=model_name, k=k) for k in k_values}

    max_k = max(k_values)

    # Evaluate
    total_queries = 0
    for sample in samples:
        chunks = sample.get("chunks", [])
        if not chunks:
            continue

        annotations = sample.get("annotations", {})
        protocol_id = sample.get("protocol_id", "unknown")

        for reg_label, ann in annotations.items():
            relevant_indices = ann.get("relevant_chunk_indices", [])
            relevance_scores = ann.get("relevance_scores", [])

            # Skip regulations with no relevant chunks in this protocol
            if not relevant_indices:
                continue

            query = REGULATION_QUERIES.get(reg_label, reg_label)
            total_queries += 1

            for model_name, evaluator in evaluators.items():
                result = evaluator.retrieve(chunks, query, k=max_k)
                result.protocol_id = protocol_id
                result.regulation = reg_label

                for k in k_values:
                    m = results[model_name][k]
                    top_k = result.retrieved_indices[:k]
                    m.recall.append(recall_at_k(top_k, relevant_indices, k))
                    m.precision.append(precision_at_k(top_k, relevant_indices, k))
                    m.mrr.append(mean_reciprocal_rank(top_k, relevant_indices))
                    m.ndcg.append(ndcg_at_k(top_k, relevant_indices, relevance_scores, k))
                    m.ap.append(average_precision(top_k, relevant_indices))
                    m.hit_rate.append(hit_rate_at_k(top_k, relevant_indices, k))
                    m.query_times_ms.append(result.query_time_ms)

    logger.info("Evaluated %d (protocol, regulation) queries across %d models", total_queries, len(evaluators))

    # Print results
    _print_results(results, k_values)

    # Save CSV if requested
    if csv_path:
        _save_csv(results, k_values, csv_path)

    # Generate plots if requested
    if plot_path:
        _generate_plots(results, k_values, plot_path)

    # Generate HTML report if requested
    if report_path:
        _generate_html_report(results, k_values, total_queries, len(samples), report_path)
        logger.info("Report saved to %s", report_path)

    return results


def _print_results(results: dict, k_values: list[int]):
    """Pretty-print evaluation results to console."""
    print(f"\n{'='*90}")
    print(f"CLARA RETRIEVAL EVALUATION RESULTS")
    print(f"{'='*90}")

    for k in k_values:
        print(f"\n┌─── k = {k} {'─'*75}")
        print(f"│ {'Model':<20} {'Recall@k':>10} {'Prec@k':>10} {'MRR':>10} "
              f"{'NDCG@k':>10} {'MAP':>10} {'HitRate':>10} {'Latency':>10}")
        print(f"│ {'─'*20} {'─'*10} {'─'*10} {'─'*10} {'─'*10} {'─'*10} {'─'*10} {'─'*10}")

        for model_name in sorted(results.keys()):
            m = results[model_name][k]
            print(
                f"│ {model_name:<20} "
                f"{m.mean('recall'):>10.3f} "
                f"{m.mean('precision'):>10.3f} "
                f"{m.mean('mrr'):>10.3f} "
                f"{m.mean('ndcg'):>10.3f} "
                f"{m.mean('ap'):>10.3f} "
                f"{m.mean('hit_rate'):>10.3f} "
                f"{m.mean('query_times_ms'):>8.1f}ms"
            )
        print(f"└{'─'*89}")

    # Recall emphasis (most important metric per CLARA's design)
    print(f"\n{'='*90}")
    print(f"RECALL ANALYSIS (primary metric — cost of missing a regulation is high)")
    print(f"{'='*90}")
    for model_name in sorted(results.keys()):
        print(f"\n  {model_name}:")
        for k in k_values:
            m = results[model_name][k]
            r = m.mean('recall')
            s = m.std('recall')
            bar = '█' * int(r * 40) + '░' * (40 - int(r * 40))
            print(f"    k={k:<3}  {bar}  {r:.3f} ± {s:.3f}")


def _save_csv(results: dict, k_values: list[int], output_path: Path):
    """Save aggregated metrics to a CSV file (one row per model × k combination)."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    metrics = ["recall", "precision", "mrr", "ndcg", "ap", "hit_rate", "query_times_ms"]
    metric_labels = {
        "recall": "Recall@k", "precision": "Precision@k", "mrr": "MRR",
        "ndcg": "NDCG@k", "ap": "MAP", "hit_rate": "HitRate", "query_times_ms": "AvgLatency_ms",
    }
    fieldnames = ["model", "k"] + [metric_labels[m] for m in metrics] + [f"{metric_labels[m]}_std" for m in metrics]

    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for model_name in sorted(results.keys()):
            for k in sorted(k_values):
                m = results[model_name][k]
                row = {"model": model_name, "k": k}
                for attr in metrics:
                    row[metric_labels[attr]] = round(m.mean(attr), 6)
                    row[f"{metric_labels[attr]}_std"] = round(m.std(attr), 6)
                writer.writerow(row)

    logger.info("CSV results saved to %s", output_path)


def _generate_html_report(
    results: dict,
    k_values: list[int],
    total_queries: int,
    total_samples: int,
    output_path: Path,
):
    """Generate an HTML report with tables and simple bar charts."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    models = sorted(results.keys())
    metrics = ["recall", "precision", "mrr", "ndcg", "ap", "hit_rate"]
    metric_labels = {
        "recall": "Recall@k", "precision": "Precision@k", "mrr": "MRR",
        "ndcg": "NDCG@k", "ap": "MAP", "hit_rate": "Hit Rate",
    }

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>CLARA Retrieval Evaluation</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 1000px; margin: 40px auto; padding: 0 20px; color: #333; }}
  h1 {{ color: #1a1a2e; border-bottom: 3px solid #e94560; padding-bottom: 10px; }}
  h2 {{ color: #16213e; margin-top: 40px; }}
  table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
  th, td {{ border: 1px solid #ddd; padding: 10px 14px; text-align: right; }}
  th {{ background: #16213e; color: white; }}
  tr:nth-child(even) {{ background: #f8f9fa; }}
  .bar {{ display: inline-block; height: 18px; background: #e94560; border-radius: 3px; vertical-align: middle; }}
  .bar-bg {{ display: inline-block; height: 18px; width: 120px; background: #eee; border-radius: 3px; position: relative; }}
  .metric-name {{ text-align: left; font-weight: 600; }}
  .summary {{ background: #f0f4f8; padding: 20px; border-radius: 8px; margin: 20px 0; }}
  .winner {{ background: #d4edda; font-weight: bold; }}
  .emphasis {{ background: #fff3cd; }}
</style></head><body>
<h1>CLARA Retrieval Evaluation Report</h1>
<div class="summary">
  <strong>Samples:</strong> {total_samples} protocols &nbsp;|&nbsp;
  <strong>Queries:</strong> {total_queries} (protocol × regulation) pairs &nbsp;|&nbsp;
  <strong>Models:</strong> {', '.join(models)} &nbsp;|&nbsp;
  <strong>k values:</strong> {', '.join(map(str, k_values))}
</div>
"""
    for k in k_values:
        html += f"<h2>Results at k = {k}</h2>\n<table>\n"
        html += f"<tr><th style='text-align:left'>Metric</th>"
        for m in models:
            html += f"<th>{m}</th>"
        html += "</tr>\n"

        for metric in metrics:
            values = {m: results[m][k].mean(metric) for m in models}
            best = max(values.values())
            is_recall = metric == "recall"
            html += f"<tr class='{'emphasis' if is_recall else ''}'>"
            html += f"<td class='metric-name'>{metric_labels[metric]}{'  ⭐' if is_recall else ''}</td>"
            for m in models:
                v = values[m]
                cls = "winner" if v == best and len(models) > 1 else ""
                bar_w = int(v * 120)
                html += (
                    f"<td class='{cls}'>"
                    f"<span class='bar-bg'><span class='bar' style='width:{bar_w}px'></span></span> "
                    f"{v:.3f}</td>"
                )
            html += "</tr>\n"

        # Latency row
        html += "<tr><td class='metric-name'>Avg Latency (ms)</td>"
        for m in models:
            lat = results[m][k].mean("query_times_ms")
            html += f"<td>{lat:.1f}</td>"
        html += "</tr>\n</table>\n"

    html += """
<h2>Notes</h2>
<ul>
  <li><strong>Recall@k</strong> is CLARA's primary metric — missing a relevant regulation
      (false negative) has higher cost than retrieving an irrelevant one (false positive).</li>
  <li>Ground truth is generated via keyword matching (silver standard). Edit
      <code>annotations.json</code> for gold-standard labels.</li>
  <li>Queries use representative eCFR text per regulation, matching the reversed-RAG
      approach in <code>server.py</code>.</li>
</ul>
</body></html>"""

    with open(output_path, "w") as f:
        f.write(html)


def _generate_plots(results: dict, k_values: list[int], output_path: Path):
    """
    Save a 2×3 grid of metric plots to output_path (PNG).

    Top row   — k-varying line plots (Recall@k ⭐, Precision@k, Hit Rate@k)
    Bottom row — k-varying NDCG@k + k-independent bar charts (MRR, MAP)

    Each line plot has a ±1 std shaded band.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")  # non-interactive backend, safe for all environments
        import matplotlib.pyplot as plt
        import matplotlib.ticker as ticker
    except ImportError:
        logger.warning("matplotlib not installed — skipping plots. Run: pip install matplotlib")
        return

    models = sorted(results.keys())
    k_sorted = sorted(k_values)
    max_k = max(k_sorted)

    # One distinct color per model (works for up to ~8 models)
    _palette = ["#e94560", "#0f3460", "#2ec4b6", "#ff9f1c", "#533483", "#44cf6c", "#f4a261", "#adb5bd"]
    model_colors = {m: _palette[i % len(_palette)] for i, m in enumerate(models)}

    fig, axes = plt.subplots(2, 3, figsize=(16, 9))
    fig.suptitle("CLARA Retrieval Evaluation — Embedding Model Comparison",
                 fontsize=13, fontweight="bold")

    # ── k-varying line plots ──────────────────────────────────────────────────
    k_panels = [
        ("recall",    "Recall@k",    True,  axes[0, 0]),
        ("precision", "Precision@k", False, axes[0, 1]),
        ("hit_rate",  "Hit Rate@k",  False, axes[0, 2]),
        ("ndcg",      "NDCG@k",      False, axes[1, 0]),
        ("mrr",       "MRR@k",       False, axes[1, 1]),
        ("ap",        "MAP@k",       False, axes[1, 2]),
    ]
    for attr, label, primary, ax in k_panels:
        for model in models:
            y   = [results[model][k].mean(attr) for k in k_sorted]
            err = [results[model][k].std(attr)  for k in k_sorted]
            lo  = [max(0.0, v - e) for v, e in zip(y, err)]
            hi  = [min(1.0, v + e) for v, e in zip(y, err)]
            ax.plot(k_sorted, y,
                    marker="o", markersize=4,
                    linewidth=2.5 if primary else 1.8,
                    label=model, color=model_colors[model])
            ax.fill_between(k_sorted, lo, hi, alpha=0.12, color=model_colors[model])

        ax.set_xlabel("k  (chunks retrieved)", fontsize=9)
        ax.set_ylabel(label, fontsize=9)
        ax.set_title(f"{label}  ⭐" if primary else label,
                     fontsize=10, fontweight="bold" if primary else "normal")
        ax.set_ylim(0, 1.08)
        ax.legend(fontsize=8, framealpha=0.85)
        ax.grid(True, alpha=0.3)
        ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info("Plots saved to %s", output_path)


# ─── CLI ──────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Evaluate CLARA retrieval strategies")
    parser.add_argument(
        "--ground-truth", "-g",
        default="test/ground_truth/annotations_full.json",
        help="Path to ground truth JSON (with full chunks)",
    )
    parser.add_argument(
        "--models", "-m",
        nargs="+",
        default=["minilm", "medsiglip", "embeddinggemma", "random"],
        choices=["minilm", "medsiglip", "embeddinggemma", "random"],
        help="Embedding models to evaluate",
    )
    parser.add_argument(
        "--k", "-k",
        nargs="+",
        type=int,
        default=[1, 2, 3, 5, 7, 10, 15, 20],
        help="Values of k for top-k retrieval metrics (more values → smoother curves)",
    )
    parser.add_argument(
        "--report", "-r",
        default="test/results/retrieval_report.html",
        help="Path for HTML report output",
    )
    parser.add_argument(
        "--plot", "-p",
        default="test/results/retrieval_curves.png",
        help="Path for PNG plot output (set to empty string to skip)",
    )
    parser.add_argument(
        "--csv", "-c",
        default="test/results/retrieval_results.csv",
        help="Path for CSV output (set to empty string to skip)",
    )
    parser.add_argument(
        "--max-samples",
        type=int,
        default=None,
        help="Limit number of protocol samples to evaluate",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    gt_path = Path(args.ground_truth)
    if not gt_path.exists():
        logger.error("Ground truth file not found: %s", gt_path)
        logger.info("Run `python test/generate_ground_truth.py` first to create it.")
        sys.exit(1)

    report_path = Path(args.report) if args.report else None
    plot_path = Path(args.plot) if args.plot else None
    csv_path = Path(args.csv) if args.csv else None
    run_evaluation(gt_path, args.models, args.k, report_path, args.max_samples, plot_path, csv_path)


if __name__ == "__main__":
    main()
