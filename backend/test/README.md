# CLARA Retrieval Evaluation Suite

Benchmarks the three embedding strategies (MedSigLIP, all-MiniLM-L6-v2, EmbeddingGemma 300M) against ground-truth regulation-to-protocol mappings.

## Quick Start

```bash
# Step 1: Generate ground truth (always works — includes synthetic protocols)
python test/generate_ground_truth.py

# Step 2: Run evaluation (uses whichever models are available locally)
python test/evaluate_retrieval.py --models minilm random --k 3 5 10

# Step 3: View the HTML report
open test/results/retrieval_report.html
```

## Ground Truth Strategy

Ground truth comes from three sources, layered by effort:

### 1. Synthetic Protocols (zero setup)
`generate_ground_truth.py` always produces 4 synthetic protocol fragments with known regulatory content. These work out-of-the-box for quick iteration:
- `SYNTH_CONSENT_FULL` — covers Parts 50, 56, 11, 46
- `SYNTH_IND_SAFETY` — covers Part 312
- `SYNTH_EMPTY_MINIMAL` — intentionally sparse (negative test)
- `SYNTH_GLP_GMP` — covers Parts 58, 211

### 2. Real Protocols (from ClinicalTrials.gov)
Download and parse real compliant protocols, then generate annotations:
```bash
python data/documents/compliant/download.py --limit 5
python data/documents/compliant/parse.py --input data/documents/compliant/protocols --output data/documents/compliant/parsed
python test/generate_ground_truth.py --protocols-dir data/documents/compliant/parsed
```
Annotations are **silver-standard** (keyword-matched). To upgrade to gold-standard, edit `test/ground_truth/annotations.json` manually — each regulation entry shows which chunk indices are relevant, and you can adjust the `relevance_scores` (2=highly relevant, 1=partial, 0=remove).

### 3. Non-Compliant Variants (redacted)
```bash
python data/documents/non_compliant/generate_negative_examples.py --limit 5
# Parse the redacted PDFs to text, then:
python test/generate_ground_truth.py -p data/documents/compliant/parsed --include-non-compliant
```
Redacted protocols provide negative examples: chunks where regulated content was removed should no longer match.

## Metrics

| Metric | What it measures | Why it matters for CLARA |
|--------|-----------------|--------------------------|
| **Recall@k** ⭐ | % of relevant chunks found in top-k | **Primary metric** — missing a regulation = undetected non-compliance |
| Precision@k | % of top-k results that are relevant | Reduces noise in MedGemma's context window |
| MRR | How early the first relevant chunk appears | Important for small k (adaptive retrieval) |
| NDCG@k | Rank-weighted relevance quality | Captures whether highly-relevant chunks rank above partial matches |
| MAP | Average precision across all recall levels | Overall ranking quality |
| Hit Rate@k | Binary: did we find anything relevant? | Minimum bar — at least one hit per regulation |

Recall@k is highlighted because CLARA's design philosophy prioritizes high recall (the writeup states: "the cost of missing a relevant regulation far exceeds the cost of retrieving an extra irrelevant passage").

## Models

| Model | Key | How to enable |
|-------|-----|---------------|
| all-MiniLM-L6-v2 | `minilm` | `pip install sentence-transformers langchain-huggingface` |
| MedSigLIP | `medsiglip` | `pip install transformers torch` + model downloads |
| EmbeddingGemma 300M | `embeddinggemma` | Set `GCP_PROJECT_ID`, `GCP_REGION` env vars + `gcloud auth` |
| Random baseline | `random` | Always available (sanity check) |

## File Structure

```
test/
├── README.md                           ← this file
├── generate_ground_truth.py            ← creates annotations from protocols
├── evaluate_retrieval.py               ← runs embedding comparison + metrics
├── ground_truth/
│   ├── annotations.json                ← compact (no chunk text)
│   └── annotations_full.json           ← with full chunk text (used by evaluator)
└── results/
    └── retrieval_report.html           ← visual comparison report
```

## Extending

**Add a new embedding model**: Add a branch in `EmbeddingEvaluator._load_embeddings()` and add its key to the `--models` CLI choices.

**Upgrade to gold-standard labels**: Edit `annotations.json`, changing `relevant_chunk_indices` and `relevance_scores` per regulation per protocol. This is especially valuable for the real ClinicalTrials.gov protocols where keyword matching may miss nuanced coverage.

**Test MMR / metadata filtering**: The current evaluator tests raw cosine similarity retrieval. To also evaluate MMR (as used in production via `lambda_mult=0.5`), wrap the ChromaDB retriever in `evaluate_retrieval.py` — the ground truth format stays the same.
