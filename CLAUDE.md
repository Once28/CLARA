# CLARA — Developer Commands

## Backend

```bash
cd backend
source venv/bin/activate

# Primary (with hot reload)
uvicorn src.server:app --reload --port 8000

# Alternative entry point
python src/app.py [port]
```

## Frontend

```bash
cd frontend
npm install
npm run dev
```

## Tests

```bash
cd backend
source venv/bin/activate

# Generate ground truth annotations
python test/generate_ground_truth.py

# Evaluate retrieval (quick smoke test with random baseline)
python test/evaluate_retrieval.py --models random

# Evaluate all models
python test/evaluate_retrieval.py --models minilm medsiglip embeddinggemma random

# Regenerate plots from existing CSV
python test/plot_results.py
```

## Project Structure

```
backend/
├── src/           ← Python source (FastAPI server, RAG pipeline)
├── test/          ← Evaluation scripts and ground truth data
├── data/          ← Chroma DB and protocol documents
├── venv/          ← Python virtual environment
├── requirements.txt
└── .env           ← GCP credentials (gitignored)
frontend/          ← React app
```
