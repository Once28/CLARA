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
from medgemma_llm import MedGemmaVertexLLM

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
_vector_db = None  # Chroma vector store (not a retriever — filters applied per request)
_graph = None


@app.on_event("startup")
async def startup():
    global _llm, _vector_db, _graph
    logger.info("Loading LLM (Vertex AI MedGemma)...")
    _llm = MedGemmaVertexLLM(
        project=os.environ["GCP_PROJECT_ID"],
        location=os.environ.get("GCP_REGION", "europe-west4"),
        endpoint_id=os.environ["VERTEX_ENDPOINT_ID"],
        temperature=0.1,
        max_tokens=4096,
    )

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
    _vector_db = initialize_rag(law_text)

    logger.info("Compiling LangGraph pipeline...")
    # Pass a default retriever to the graph (unfiltered, for the standalone pipeline)
    _default_retriever = _vector_db.as_retriever(
        search_type="mmr",
        search_kwargs={"k": 5, "fetch_k": 20, "lambda_mult": 0.5},
    )
    _graph = create_rip_graph(_default_retriever, _llm)
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
You are an FDA auditor. Audit the protocol below against the listed regulations.

REGULATORY CONTEXT:
{context}

PROTOCOL (excerpt):
{protocol}

REGULATIONS: {regulations}

TASK: Produce EXACTLY one JSON object per regulation listed above.
The total number of objects in the array MUST equal the number of regulations.
Do NOT split a single regulation into multiple objects.
Summarize ALL findings for each regulation into its single object.

Each object has these keys:
  regulation  – the regulation label, e.g. "21 CFR Part 50"
  status      – "pass", "warning", or "critical" (overall for that regulation)
  note        – one sentence overall summary
  focus       – comma-separated list of aspects examined
  gaps        – list of specific gap strings (empty list [] if pass)
  remediation – list of fix strings (empty list [] if pass)

Output ONLY a valid JSON array. No markdown, no commentary.

Example with 2 regulations:
[{{"regulation":"21 CFR Part 11","status":"warning","note":"Partial audit trail coverage.","focus":"Audit trails, e-signatures","gaps":["No system validation"],"remediation":["Add 11.10(a) docs"]}},{{"regulation":"21 CFR Part 50","status":"pass","note":"Informed consent procedures are adequate.","focus":"Informed consent, vulnerable populations","gaps":[],"remediation":[]}}]

JSON array:
"""


def _sanitize_json_string(raw: str) -> str:
    """Clean common small-model JSON mistakes so json.loads can succeed."""
    s = raw.strip()

    # Strip MedGemma thinking/reasoning blocks (e.g. <thought>...</thought> or thought...JSON)
    # The model sometimes prefixes output with "thought" followed by reasoning text
    s = re.sub(r"^<thought>.*?</thought>\s*", "", s, flags=re.DOTALL)
    s = re.sub(r"^thought\s*.*?(?=\[)", "", s, flags=re.DOTALL)

    # Strip markdown code fences
    s = re.sub(r"^```(?:json)?\s*", "", s)
    s = re.sub(r"\s*```$", "", s)

    # Remove JavaScript-style comments  ( // … )
    s = re.sub(r"//[^\n]*", "", s)

    # Replace single quotes with double quotes (naive but helpful)
    # Only do this if there are no double quotes already wrapping keys
    if '"' not in s and "'" in s:
        s = s.replace("'", '"')

    # Fix trailing commas before ] or }
    s = re.sub(r",\s*([\]\}])", r"\1", s)

    # Fix missing commas between }{ (objects not separated)
    s = re.sub(r"\}\s*\{", "},{" , s)

    return s.strip()


def _extract_findings_from_freetext(raw: str, regulations: str) -> list[dict]:
    """Last-resort: pull findings from free-text LLM output."""
    results = []
    reg_labels = [r.strip() for r in regulations.split(",")] if regulations else ["General"]

    # Try to detect status keywords per regulation mention
    for label in reg_labels:
        # Determine status from surrounding text
        status = "warning"  # default
        lower_raw = raw.lower()
        label_lower = label.lower()

        # Look for the regulation label in the text and nearby keywords
        idx = lower_raw.find(label_lower)
        if idx == -1:
            # Try partial match (e.g. "part 50")
            part_match = re.search(r"part\s*(\d+)", label_lower)
            if part_match:
                idx = lower_raw.find(f"part {part_match.group(1)}")

        nearby = lower_raw[max(0, idx-200):idx+500] if idx != -1 else lower_raw

        if any(w in nearby for w in ["critical", "violation", "missing", "fail", "absent", "not found", "not addressed"]):
            status = "critical"
        elif any(w in nearby for w in ["pass", "compliant", "adequate", "present", "addressed", "met", "sufficient"]):
            status = "pass"

        # Try to extract a useful sentence near the regulation mention
        note = "See raw audit output for details."
        if idx != -1:
            # Grab the sentence around the mention
            snippet = raw[max(0, idx):idx+300]
            sentences = re.split(r"[.\n]", snippet)
            for sent in sentences:
                cleaned = sent.strip()
                if len(cleaned) > 20:
                    note = (cleaned[:150] + "...") if len(cleaned) > 150 else cleaned
                    break

        results.append({
            "regulation": label,
            "status": status,
            "note": note,
            "focus": "Extracted from free-text audit output",
            "gaps": ["Review raw audit text for specific gaps"] if status != "pass" else [],
            "remediation": ["Review raw audit text for recommendations"] if status != "pass" else [],
        })

    return results


def parse_structured_output(raw: str, regulations: str = "") -> list[dict]:
    """
    Try to extract a JSON array from the LLM response.
    Falls back to free-text extraction if JSON parsing fails entirely.
    """
    logger.info("Raw LLM output (%d chars): %.500s...", len(raw), raw)

    sanitized = _sanitize_json_string(raw)

    # Attempt 1: direct parse
    try:
        data = json.loads(sanitized)
        if isinstance(data, list):
            logger.info("Parsed JSON array directly (%d items)", len(data))
            return data
        if isinstance(data, dict):
            return [data]
    except json.JSONDecodeError:
        pass

    # Attempt 2: find the outermost [...] in the text
    match = re.search(r"\[.*\]", sanitized, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group())
            if isinstance(data, list):
                logger.info("Parsed JSON array from regex match (%d items)", len(data))
                return data
        except json.JSONDecodeError:
            pass

    # Attempt 3: find individual JSON objects and collect them
    objects = []
    for m in re.finditer(r"\{[^{}]*\}", sanitized):
        try:
            obj = json.loads(m.group())
            if "status" in obj or "regulation" in obj:
                objects.append(obj)
        except json.JSONDecodeError:
            continue
    if objects:
        logger.info("Parsed %d individual JSON objects from text", len(objects))
        return objects

    # Attempt 4: free-text extraction
    logger.warning("JSON parse failed — falling back to free-text extraction")
    results = _extract_findings_from_freetext(raw, regulations)
    if results:
        return results

    # Final fallback
    return [{
        "regulation": "All",
        "status": "critical",
        "note": "LLM output could not be parsed. Raw output is available in queryDescription.",
        "focus": "N/A",
        "gaps": ["Structured parsing failed — review raw audit output."],
        "remediation": ["Re-run audit or review raw LLM output."],
    }]


def _merge_duplicate_regulations(items: list[dict]) -> list[dict]:
    """
    If the LLM produced multiple objects for the same regulation,
    merge them into one entry per regulation.
    """
    from collections import OrderedDict

    STATUS_PRIORITY = {"critical": 0, "warning": 1, "pass": 2}
    merged: OrderedDict[str, dict] = OrderedDict()

    for item in items:
        key = item.get("regulation", "Unknown").strip()
        if key not in merged:
            merged[key] = {
                "regulation": key,
                "status": item.get("status", "warning"),
                "note": item.get("note", ""),
                "focus": item.get("focus", ""),
                "gaps": list(item.get("gaps", [])),
                "remediation": list(item.get("remediation", [])),
            }
        else:
            existing = merged[key]
            # Keep the worst status
            new_status = item.get("status", "warning")
            if STATUS_PRIORITY.get(new_status, 1) < STATUS_PRIORITY.get(existing["status"], 1):
                existing["status"] = new_status
            # Append unique gaps and remediations
            for gap in item.get("gaps", []):
                if gap and gap not in existing["gaps"]:
                    existing["gaps"].append(gap)
            for rem in item.get("remediation", []):
                if rem and rem not in existing["remediation"]:
                    existing["remediation"].append(rem)
            # Combine focus areas
            new_focus = item.get("focus", "")
            if new_focus and new_focus not in existing["focus"]:
                existing["focus"] = f"{existing['focus']}, {new_focus}"
            # Keep the more detailed note
            new_note = item.get("note", "")
            if len(new_note) > len(existing["note"]):
                existing["note"] = new_note

    result = list(merged.values())
    if len(result) < len(items):
        logger.info("Merged %d LLM items → %d unique regulations", len(items), len(result))
    return result


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
    if _graph is None or _vector_db is None:
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

    # Retrieval step — search only within the selected regulations
    # Build a Chroma metadata filter for the user's regulation selection
    if len(reg_labels) == 1:
        where_filter = {"cfr_part": reg_labels[0]}
    else:
        where_filter = {"cfr_part": {"$in": reg_labels}}

    filtered_retriever = _vector_db.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": min(3 * len(reg_labels), 15),  # ~3 chunks per regulation
            "fetch_k": min(8 * len(reg_labels), 40),
            "lambda_mult": 0.5,
            "filter": where_filter,
        },
    )
    docs = filtered_retriever.invoke(protocol_text[:3000])  # query with start of protocol
    retrieved_regulations = [d.page_content for d in docs]
    context = "\n\n".join(retrieved_regulations)
    logger.info("Retrieved %d regulation chunks for: %s", len(docs), regulations_text)

    # Build retrieved sections for the frontend
    retrieved_sections = []
    for i, doc in enumerate(docs):
        cfr_label = doc.metadata.get("cfr_part", "Unknown")
        snippet = doc.page_content[:80].replace("\n", " ").strip()
        retrieved_sections.append(f"[{cfr_label}] {snippet}...")

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
        if "Connection refused" in err_msg or "ConnectError" in err_msg or "403" in err_msg:
            raise HTTPException(
                503,
                "Cannot connect to Google Cloud Vertex AI. Make sure your GCP_PROJECT_ID "
                "and GCP_REGION are set correctly, and MedGemma is deployed in Model Garden."
            )
        raise HTTPException(500, f"LLM inference failed: {err_msg}")
    logger.info(f"LLM response length: {len(raw_response)} chars")
    logger.info(f"Raw LLM response (first 1000 chars): {raw_response[:1000]}")

    # 4. Parse structured output
    breakdown = parse_structured_output(raw_response, regulations_text)

    # 4b. Merge duplicate regulation entries (e.g. if LLM split Part 50 into 20 objects)
    breakdown = _merge_duplicate_regulations(breakdown)

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
        "rawLlmOutput": raw_response,
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
