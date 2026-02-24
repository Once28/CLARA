<h1>
  <img src="assets/CLARA.svg" alt="CLARA Logo" width="40" align="center"/>
  CLARA: CLinical Audit & Regulatory Assistant 🩺💜
</h1>

CLARA, derived from the latin _Clarus_, is an agentic platform built for the MedGemma Impact Challenge. CLARA automates the regulatory cross-examination of clinical trial protocols, tested on **21 CFR** (Parts 11, 50, 56, 58, 211, 312, 314, etc.) and **45 CFR Part 46** (Common Rule). The name CLARA and term _Clarus_ reinforces what we stand for: clarity in complex decisions, trust in high-stakes clinical environments, and a human presence within AI that feels supportive rather than technical. In healthcare, intelligence must be clear, reliable, and approachable — and CLARA embodies all three.

![CLARA System Architecture](data/md/CLARA.png)
<p align="center"><em>Figure 1: CLARA System Architecture</em></p>


CLARA tackles the critical bottleneck in clinical trials: regulatory compliance checking. By combining RAG with an FDA-auditor LLM (MedGemma via Vertex AI), CLARA automates the cross-examination of clinical trial protocols against FDA and HHS regulations.

So the protocol is the source of truth in the index; regulations are checked against it (rather than the other way around).

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- A Gemini API key (free at [aistudio.google.com](https://aistudio.google.com/apikey)) **or** a Google Cloud project with a deployed MedGemma Vertex AI endpoint
- Run `gcloud auth application-default login` if using Vertex AI

### 1. Backend Setup

```bash
cd backend

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # macOS / Linux
# venv\Scripts\activate         # Windows

# Install Python dependencies
pip install -r requirements.txt

# Copy and fill environment variables
cp .env_sample .env
# At minimum, set GEMINI_API_KEY for the Gemini Flash placeholder LLM.
# For MedGemma (Vertex AI), set GCP_PROJECT_ID, GCP_REGION, VERTEX_ENDPOINT_ID instead.

# Start the FastAPI backend
uvicorn src.server:app --reload --port 8000
```

### 2. Frontend Setup

In a separate terminal:

```bash
cd frontend
npm install
npm run dev
```

The React frontend is served at `http://localhost:5173`. The Vite dev server proxies all `/api/*` requests to the backend at `http://localhost:8000` — no CORS configuration required.

## 📁 Directory Guide

```
CLARA/
├── README.md
├── WRITEUP.md              # MedGemma Impact Challenge submission
├── backend/
│   ├── src/
│   │   ├── server.py       # FastAPI server — upload, audit, list, delete endpoints
│   │   ├── app.py          # Uvicorn entry point (alternative to uvicorn CLI)
│   │   ├── gemini_llm.py   # Gemini 1.5 Flash LLM wrapper (free placeholder)
│   │   ├── medgemma_llm.py # MedGemma via Vertex AI (production LLM)
│   │   ├── vector_store.py # Reversed RAG: protocol chunks as KB, CFR as query
│   │   ├── ecfr_client.py  # Live eCFR API client (21/45 CFR)
│   │   ├── graph.py        # LangGraph workflow definition
│   │   ├── nodes.py        # Retrieval and audit node implementations
│   │   ├── state.py        # Agent state schema (TypedDict)
│   │   └── prompts.py      # System prompts for FDA auditor persona
│   ├── test/
│   │   ├── evaluate_retrieval.py   # Retrieval benchmarking (precision, recall, NDCG)
│   │   ├── generate_ground_truth.py
│   │   ├── plot_results.py
│   │   ├── ground_truth/   # Annotated retrieval ground truth
│   │   └── results/        # Benchmark output (HTML report, CSV, PNG curves)
│   ├── data/
│   │   ├── chroma_db/      # Persistent vector database
│   │   └── documents/      # Sample protocols (compliant & non-compliant)
│   ├── requirements.txt
│   └── .env                # GEMINI_API_KEY, rate limits, Vertex AI config
├── frontend/
│   ├── src/
│   │   ├── App.jsx         # Root application component
│   │   ├── components/     # UI components (Header, Sidebar, modals, tutorial)
│   │   ├── hooks/          # Custom React hooks (useAudits)
│   │   ├── services/       # API client (api.js)
│   │   └── styles/         # Global CSS
│   ├── .env                # VITE_USE_MOCK=false (leave VITE_API_URL empty for proxy)
│   └── package.json
└── assets/                 # Logos and static images
```

## 🔧 Core Components

**`backend/src/server.py`** - FastAPI Backend (primary)
- On startup: auto-detects LLM — uses Gemini 1.5 Flash if `GEMINI_API_KEY` is set, otherwise MedGemma via Vertex AI. Fetches all CFR parts from the eCFR API.
- On protocol upload: enforces rate limits (3/min, 50/day) and file size cap (10 MB), then extracts text, chunks and embeds it via `vector_store.index_protocol`. For each CFR regulation runs `query_protocol_for_regulation` (reversed RAG), builds context, and runs the LLM audit with structured output.

**`backend/src/gemini_llm.py`** / **`medgemma_llm.py`** - LLM Wrappers
- `GeminiFlashLLM`: free placeholder using `gemini-1.5-flash` via the Gemini API. Activated when `GEMINI_API_KEY` is present in `.env`.
- `MedGemmaVertexLLM`: production LLM using MedGemma deployed on Vertex AI. Used when no Gemini key is set.

**`backend/src/graph.py`** - Workflow Engine
- Defines LangGraph state machine
- Connects retrieval → audit nodes
- Compiles executable graph

**`backend/src/nodes.py`** - Processing Nodes (LangGraph / standalone app)
- **retrieval_node**: Uses a retriever for the graph-based flow.
- **audit_node**: Performs LLM-based regulatory analysis. The main API flow in `server.py` uses its own reversed RAG path (protocol index + CFR-as-query) and structured prompt.

**`backend/src/state.py`** - State Management
```python
AgentState:
  - protocol_text: str              # Input protocol section
  - retrieved_regulations: List[str] # Relevant CFR sections
  - audit_results: str               # Compliance analysis
  - compliance_score: int            # 1-100 score (future)
```

**`backend/src/ecfr_client.py`** - Regulatory Data
- Fetches live 21 CFR (Parts 11, 46, 50, 56, 58, 211, 312, 314) and 45 CFR Part 46 from eCFR.gov API
- Generic `get_part(title, part)` for any CFR title/part

**`backend/src/vector_store.py`** - RAG
- **Protocol as knowledge base:** Uploaded protocols are chunked (RecursiveCharacterTextSplitter), embedded (HuggingFace sentence-transformers), and stored in Chroma (`protocol_chunks` collection).
- **CFR as query:** For each CFR regulation, the regulation text is used as the search query; the retriever returns the top-k protocol chunks that address it (MMR for diversity).
- No CFR text is stored in the vector store; only protocol chunks are indexed.

**`backend/src/prompts.py`** - Prompt Engineering
- FDA Regulatory Auditor persona
- Structured instructions for compliance checking
- Focus on electronic signatures and audit trails

## 📄 License

This project is built for the MedGemma Impact Challenge. Contributions are welcome! Please open an issue or submit a pull request. For questions about this project, please refer to [WRITEUP.md](WRITEUP.md) for technical documentation used for MedGamme submission.
