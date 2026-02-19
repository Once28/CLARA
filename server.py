"""
FastAPI server wrapping the existing CLARA pipeline.

Start with:
    uvicorn server:app --reload --port 8000

The React frontend connects by setting:
    VITE_API_URL=http://localhost:8000
"""

import os, uuid, json, re, logging
from datetime import date
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from PyPDF2 import PdfReader
import io

from ecfr_client import ECFRClient
from vector_store import initialize_rag
from graph import create_rip_graph
from langchain_ollama import OllamaLLM

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("clara")

# ─── App ──────────────────────────────────────────────────────

app = FastAPI(title="CLARA API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Pipeline init (runs once at startup) ─────────────────────

REGULATION_MAP = {
    "21_cfr_11":  ("21 CFR Part 11",  ECFRClient.get_part_11_text),
    "21_cfr_50":  ("21 CFR Part 50",  ECFRClient.get_part_50_text),
    "21_cfr_56":  ("21 CFR Part 56",  ECFRClient.get_part_56_text),
    "21_cfr_58":  ("21 CFR Part 58",  ECFRClient.get_part_58_text),
    "21_cfr_211": ("21 CFR Part 211", ECFRClient.get_part_211_text),
    "21_cfr_312": ("21 CFR Part 312", ECFRClient.get_part_312_text),
    "21_cfr_314": ("21 CFR Part 314", ECFRClient.get_part_314_text),
    "45_cfr_46":  ("45 CFR Part 46",  ECFRClient.get_part_45_46_text),
}

# These are populated at startup
_llm = None
_retriever = None
_graph = None


@app.on_event("startup")
async def startup():
    global _llm, _retriever, _graph
    logger.info("Loading LLM...")
    _llm = OllamaLLM(model="MedAIBase/MedGemma1.5:4b", temperature=0.1)

    logger.info("Fetching eCFR regulations...")
    law_text_parts = []
    for key, (label, fetcher) in REGULATION_MAP.items():
        try:
            xml = fetcher()
            law_text_parts.append(f"\n\n<!-- {label} -->\n{xml}")
            logger.info(f"  ✓ {label}")
        except Exception as e:
            logger.warning(f"  ✗ {label}: {e}")

    law_text = "\n".join(law_text_parts) if law_text_parts else ""
    logger.info("Building vector store...")
    _retriever = initialize_rag(law_text)

    logger.info("Compiling LangGraph pipeline...")
    _graph = create_rip_graph(_retriever, _llm)
    logger.info("CLARA API ready.")


# ─── In-memory audit store ────────────────────────────────────

_audits: dict[str, dict] = {}  # id -> audit dict


def _next_id() -> str:
    """Sequential 3-digit ID."""
    n = len(_audits) + 1
    return f"{n:03d}"


def compute_score(breakdown: list[dict]) -> int:
    if not breakdown:
        return 0
    STATUS_SCORE = {"pass": 100, "warning": 50, "critical": 0}
    total = sum(STATUS_SCORE.get(item.get("status", ""), 0) for item in breakdown)
    return round(total / len(breakdown))


# ─── Structured output prompt ─────────────────────────────────

STRUCTURED_AUDIT_PROMPT = """
You are a Senior FDA Regulatory Auditor with expertise in 21 CFR and 45 CFR regulations.

REGULATORY CONTEXT (retrieved CFR sections):
{context}

PROTOCOL TEXT:
{protocol}

REGULATIONS TO AUDIT AGAINST:
{regulations}

INSTRUCTIONS:
Evaluate the protocol against EACH of the listed regulations. For each regulation produce a JSON object.

Respond with ONLY a valid JSON array (no markdown, no extra text). Each element must have exactly these fields:
- "regulation": short label like "21 CFR P50: Protection of Human Subjects"
- "status": one of "pass", "warning", or "critical"
- "note": one-sentence summary of the finding
- "focus": what aspects of the regulation were examined
- "gaps": array of specific compliance gap strings (empty array if status is "pass")
- "remediation": array of recommended fix strings (empty array if status is "pass")

Example of ONE element:
{{"regulation":"21 CFR P11: Electronic Records","status":"warning","note":"Partial coverage of audit trail requirements.","focus":"Audit trails, e-signatures, system validation.","gaps":["No system validation described."],"remediation":["Add validation documentation per 21 CFR 11.10(a)."]}}

Return ONLY the JSON array. No explanation before or after.
"""


def parse_structured_output(raw: str) -> list[dict]:
    """Try to extract a JSON array from the LLM response."""
    # Try direct parse first
    raw = raw.strip()
    if raw.startswith("```"):
        # Strip markdown code fences
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass

    # Try to find a JSON array in the text
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group())
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass

    # Fallback: return a single critical item indicating parse failure
    return [{
        "regulation": "All",
        "status": "critical",
        "note": "LLM output could not be parsed into structured format. Raw output is available in queryDescription.",
        "focus": "N/A",
        "gaps": ["Structured parsing failed — review raw audit output."],
        "remediation": ["Re-run audit or review raw LLM output."],
    }]


# ─── PDF text extraction ──────────────────────────────────────

def extract_text_from_pdf(contents: bytes) -> str:
    reader = PdfReader(io.BytesIO(contents))
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text:
            pages.append(f"[Page {i+1}]\n{text}")
    return "\n\n".join(pages)


# ─── Routes ───────────────────────────────────────────────────

@app.get("/api/audits")
async def list_audits():
    """Return all audits, most recent first."""
    return sorted(_audits.values(), key=lambda a: a["uploadDate"], reverse=True)


@app.get("/api/audits/{audit_id}")
async def get_audit(audit_id: str):
    audit = _audits.get(audit_id)
    if not audit:
        raise HTTPException(404, f"Audit {audit_id} not found")
    return audit


@app.delete("/api/audits/{audit_id}")
async def delete_audit(audit_id: str):
    if audit_id not in _audits:
        raise HTTPException(404, f"Audit {audit_id} not found")
    del _audits[audit_id]
    return {"success": True}


@app.post("/api/audits/upload")
async def upload_protocol(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    phase: Optional[str] = Form(None),
    sponsor: Optional[str] = Form(None),
    regulations: Optional[str] = Form(None),  # comma-separated reg keys
):
    """Upload a protocol PDF, run the audit pipeline, return structured results."""
    if _graph is None:
        raise HTTPException(503, "Pipeline not initialized yet — server is still starting up.")

    # 1. Extract text
    contents = await file.read()
    if file.filename and file.filename.lower().endswith(".pdf"):
        protocol_text = extract_text_from_pdf(contents)
    else:
        protocol_text = contents.decode("utf-8", errors="replace")

    if not protocol_text.strip():
        raise HTTPException(400, "Could not extract any text from the uploaded file.")

    # 2. Determine which regulations to audit against
    if regulations:
        reg_keys = [r.strip() for r in regulations.split(",")]
    else:
        reg_keys = list(REGULATION_MAP.keys())

    reg_labels = [REGULATION_MAP[k][0] for k in reg_keys if k in REGULATION_MAP]
    regulations_text = ", ".join(reg_labels)

    # 3. Run retrieval + LLM audit via the LangGraph pipeline
    logger.info(f"Running audit for '{file.filename}' against: {regulations_text}")

    # Retrieval step — get relevant regulation sections
    docs = _retriever.invoke(protocol_text)
    retrieved_regulations = [d.page_content for d in docs]
    context = "\n\n".join(retrieved_regulations)

    # Build retrieved sections for the frontend
    retrieved_sections = []
    for i, doc in enumerate(docs):
        # Try to get a meaningful label from the doc
        snippet = doc.page_content[:80].replace("\n", " ").strip()
        retrieved_sections.append(f"Section {i+1} – {snippet}...")

    # Audit step — use structured prompt
    formatted_prompt = STRUCTURED_AUDIT_PROMPT.format(
        context=context,
        protocol=protocol_text[:8000],  # Truncate to avoid exceeding context
        regulations=regulations_text,
    )
    try:
        raw_response = _llm.invoke(formatted_prompt)
    except Exception as e:
        err_msg = str(e)
        if "Connection refused" in err_msg or "ConnectError" in err_msg:
            raise HTTPException(
                503,
                "Cannot connect to Ollama. Make sure Ollama is running (ollama serve) "
                "and the MedGemma model is available (ollama run MedAIBase/MedGemma1.5:4b)."
            )
        raise HTTPException(500, f"LLM inference failed: {err_msg}")
    logger.info(f"LLM response length: {len(raw_response)} chars")

    # 4. Parse structured output
    breakdown = parse_structured_output(raw_response)

    # 5. Compute score
    score = compute_score(breakdown)

    # 6. Build audit object matching frontend shape
    audit_id = _next_id()
    audit = {
        "id": audit_id,
        "filename": file.filename or "unknown.pdf",
        "uploadDate": date.today().isoformat(),
        "approvalStatus": "approved" if score >= 75 else "not approved",
        "phase": phase or "Unknown",
        "score": score,
        "queryDescription": (
            f"Regulatory nodes were matched against \"{title or file.filename}\" protocol content "
            f"using semantic similarity scoring against: {regulations_text}. "
            f"Retrieved {len(docs)} relevant sections."
        ),
        "retrievedSections": retrieved_sections,
        "breakdown": breakdown,
    }

    _audits[audit_id] = audit
    logger.info(f"Audit {audit_id} complete — score: {score}")
    return audit


# ─── Health check ─────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "pipeline_ready": _graph is not None,
        "audits_count": len(_audits),
    }
