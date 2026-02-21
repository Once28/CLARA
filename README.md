<h1>
  <img src="data/md/CLARA.svg" alt="CLARA Logo" width="40" align="center"/>
  CLARA: CLinical Audit & Regulatory Assistant 🩺💜
</h1>

A multi-modal agentic platform built for the MedGemma Impact Challenge. It automates the "Regulatory Cross-Examination" of clinical trial protocols, ensuring alignment with **21 CFR** (Parts 11, 50, 56, 58, 211, 312, 314, etc.) and **45 CFR Part 46** (Common Rule) before a single patient is enrolled.

![CLARA System Architecture](data/md/CLARA.png)
<p align="center"><em>Figure 1: CLARA System Architecture</em></p>


**CLARA** tackles the critical bottleneck in clinical trials: regulatory compliance checking. By combining **reversed RAG** with an FDA-auditor LLM (MedGemma via Vertex AI), CLARA automates the cross-examination of clinical trial protocols against FDA and HHS regulations.

### Reversed RAG Design

- **Knowledge base:** The **uploaded protocol** is chunked, embedded, and stored in a vector index (Chroma).
- **Query side:** Each **CFR regulation** (21 CFR Parts 11, 50, 56, 58, 211, 312, 314; 45 CFR Part 46) is used as a query against the protocol index to find which protocol sections address it.
- **Audit:** The LLM receives, for each regulation, the regulation excerpt and the retrieved protocol sections, and produces a structured compliance breakdown.

So the protocol is the source of truth in the index; regulations are checked against it (rather than the other way around).

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- Google Cloud project with Vertex AI and MedGemma endpoint (see `.env_sample` and root `.env`)
- Run `gcloud auth application-default login` for API auth

### 1. Backend Setup

```bash
# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # macOS / Linux
# venv\Scripts\activate         # Windows

# Install Python dependencies
pip install -r requirements.txt

# Copy and fill environment variables
cp .env_sample .env
# Set GCP_PROJECT_ID, GCP_REGION, VERTEX_ENDPOINT_ID, etc.

# Start the FastAPI backend
uvicorn server:app --reload --port 8000
```

### 2. Frontend Setup

In a separate terminal:

```bash
cd frontend
npm install
npm run dev
```

The React frontend connects to the backend at `http://localhost:8000` (configured via `VITE_API_URL` in `frontend/.env`).

## 📁 Directory Guide

```
CLARA/
├── server.py               # FastAPI backend (serves the React frontend)
├── graph.py                # LangGraph workflow definition
├── nodes.py                # Retrieval and audit node implementations
├── state.py                # Agent state schema (TypedDict)
├── prompts.py              # System prompts for FDA auditor persona
├── ecfr_client.py          # eCFR API client for 21/45 CFR (Parts 11, 50, 56, 312, 211, etc.)
├── vector_store.py         # Reversed RAG: protocol chunks as KB, CFR as query
├── requirements.txt        # Python dependencies
├── README.md               # This file
├── WRITEUP.md              # MedGemma Impact Challenge submission
├── frontend/               # React + Vite UI
│   ├── src/
│   │   ├── App.jsx         # Root application component
│   │   ├── components/     # UI components
│   │   ├── hooks/          # Custom React hooks (useAudits)
│   │   ├── services/       # API client (api.js)
│   │   └── styles/         # Global CSS
│   └── package.json
├── data/
│   ├── chroma_db/          # Persistent vector database
│   └── documents/          # Sample protocols (compliant & non-compliant)
└── test/
    ├── pipeline.ipynb      # Development testing notebook
    └── medgamma.ipynb      # MedGemma integration experiments
```

## 🔧 Core Components

<<<<<<< HEAD
### 1. **server.py** - FastAPI Backend
- Fetches multiple CFR parts (11, 50, 56, 58, 211, 312, 314, 45 CFR 46) via eCFR API
- Initializes RAG system and LLM at startup
- Exposes REST API for audit upload, retrieval, and deletion
- Runs per-request metadata-filtered RAG retrieval and structured LLM audit
=======
### 1. **server.py** - FastAPI Backend (primary)
- On startup: loads MedGemma (Vertex AI) and fetches CFR parts from eCFR API.
- On protocol upload: extracts text, chunks and embeds it via `vector_store.index_protocol`, then for each selected CFR regulation runs `query_protocol_for_regulation` (reversed RAG), builds context, and runs the LLM audit with structured output.
>>>>>>> 5fb04a88e034502960c9660582cb3601462e2bc9

### 2. **graph.py** - Workflow Engine
- Defines LangGraph state machine
- Connects retrieval → audit nodes
- Compiles executable graph

### 3. **nodes.py** - Processing Nodes (LangGraph / standalone app)
- **retrieval_node**: Uses a retriever for the graph-based flow.
- **audit_node**: Performs LLM-based regulatory analysis. The main API flow in `server.py` uses its own reversed RAG path (protocol index + CFR-as-query) and structured prompt.

### 4. **state.py** - State Management
```python
AgentState:
  - protocol_text: str              # Input protocol section
  - retrieved_regulations: List[str] # Relevant CFR sections
  - audit_results: str               # Compliance analysis
  - compliance_score: int            # 1-100 score (future)
```

### 5. **ecfr_client.py** - Regulatory Data
- Fetches live 21 CFR (Parts 11, 46, 50, 56, 58, 211, 312, 314) and 45 CFR Part 46 from eCFR.gov API
- Generic `get_part(title, part)` for any CFR title/part

### 6. **vector_store.py** - RAG
- **Protocol as knowledge base:** Uploaded protocols are chunked (RecursiveCharacterTextSplitter), embedded (HuggingFace sentence-transformers), and stored in Chroma (`protocol_chunks` collection).
- **CFR as query:** For each CFR regulation, the regulation text is used as the search query; the retriever returns the top-k protocol chunks that address it (MMR for diversity).
- No CFR text is stored in the vector store; only protocol chunks are indexed.

### 7. **prompts.py** - Prompt Engineering
- FDA Regulatory Auditor persona
- Structured instructions for compliance checking
- Focus on electronic signatures and audit trails

## 📄 License

This project is built for the MedGemma Impact Challenge. Contributions are welcome! Please open an issue or submit a pull request. For questions about this project, please refer to [WRITEUP.md](WRITEUP.md) for technical documentation used for MedGamme submission.
