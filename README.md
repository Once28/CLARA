# CLARA: CLinical Audit & Regulatory Assistant　🩺💜

A multi-modal agentic platform built for the MedGemma Impact Challenge. It automates the "Regulatory Cross-Examination" of clinical trial protocols, ensuring alignment with **21 CFR** (Parts 11, 50, 56, 58, 211, 312, 314, etc.) and **45 CFR Part 46** (Common Rule) before a single patient is enrolled.

![CLARA System Architecture](data/md/CLARA.png)
<p align="center"><em>Figure 1: CLARA System Architecture</em></p>


**CLARA** tackles the critical bottleneck in clinical trials: regulatory compliance checking. By combining Retrieval-Augmented Generation (RAG) with LangGraph's agentic workflow, CLARA automates the cross-examination of clinical trial protocols against FDA and HHS regulations, freeing researchers to focus on innovation rather than grunt work.

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 18+
- [Ollama](https://ollama.com/) installed locally
- API keys configured in a `.env` file (see `frontend/.env` and root `.env`)

### 1. Install MedGemma 4B (via Ollama)

CLARA runs the **MedGemma 1.5 4B** model locally through Ollama.
We plan to update this later.

```bash
# Install Ollama (macOS)
brew install ollama
# Start the Ollama server (keep this running in a separate terminal)
ollama serve
# Pull the MedGemma 4B model (~2.5 GB download)
ollama pull MedAIBase/MedGemma1.5:4b
```

Verify the model is working:

```bash
ollama run MedAIBase/MedGemma1.5:4b "Hello"
```

> **Note:** The Ollama server must be running (`ollama serve`) before starting the CLARA backend.

### 2. Backend Setup

```bash
# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # macOS / Linux
# venv\Scripts\activate         # Windows

# Install Python dependencies
pip install -r requirements.txt

# Start the FastAPI backend
uvicorn server:app --reload --port 8000
```

### 3. Frontend Setup

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
├── vector_store.py         # ChromaDB RAG initialization
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

### 1. **server.py** - FastAPI Backend
- Fetches multiple CFR parts (11, 50, 56, 58, 211, 312, 314, 45 CFR 46) via eCFR API
- Initializes RAG system and LLM at startup
- Exposes REST API for audit upload, retrieval, and deletion
- Runs per-request metadata-filtered RAG retrieval and structured LLM audit

### 2. **graph.py** - Workflow Engine
- Defines LangGraph state machine
- Connects retrieval → audit nodes
- Compiles executable graph

### 3. **nodes.py** - Processing Nodes
- **retrieval_node**: Queries vector store for relevant regulations
- **audit_node**: Performs LLM-based regulatory analysis

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

### 6. **vector_store.py** - RAG System
- ChromaDB for persistent vector storage
- HuggingFace embeddings (sentence-transformers)
- Returns top 5 relevant regulation chunks

### 7. **prompts.py** - Prompt Engineering
- FDA Regulatory Auditor persona
- Structured instructions for compliance checking
- Focus on electronic signatures and audit trails

## 📄 License

This project is built for the MedGemma Impact Challenge. Contributions are welcome! Please open an issue or submit a pull request. For questions about this project, please refer to [WRITEUP.md](WRITEUP.md) for technical documentation used for MedGamme submission.