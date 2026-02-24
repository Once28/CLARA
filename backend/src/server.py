"""
FastAPI server wrapping the existing CLARA pipeline.

Start with:
    uvicorn server:app --reload --port 8000

The React frontend connects by setting:
    VITE_API_URL=http://localhost:8000
"""

import os, uuid, json, re, logging, time
from collections import deque
from datetime import date
from threading import Lock
from typing import Optional

from dotenv import load_dotenv
load_dotenv()
from PyPDF2 import PdfReader
import io

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .ecfr_client import ECFRClient
from .vector_store import (
    get_embeddings,
    index_protocol,
    query_protocol_for_regulation,
)
from .medgemma_llm import MedGemmaVertexLLM
from .gemini_llm import GeminiFlashLLM

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

# ─── Abuse protection ─────────────────────────────────────────

_MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_MB", "10")) * 1024 * 1024


class _RateLimiter:
    """Global in-memory rate limiter: per-minute burst + daily cap."""

    def __init__(self):
        self._lock = Lock()
        self._minute_window: deque = deque()
        self._day_count: int = 0
        self._day_reset: float = time.time() + 86400
        # Configurable via env — defaults suit a shared demo instance
        self.max_per_minute: int = int(os.environ.get("RATE_LIMIT_PER_MINUTE", "3"))
        self.max_per_day: int = int(os.environ.get("RATE_LIMIT_PER_DAY", "50"))

    def check(self) -> tuple[bool, str]:
        with self._lock:
            now = time.time()
            if now > self._day_reset:
                self._day_count = 0
                self._day_reset = now + 86400
            if self._day_count >= self.max_per_day:
                return False, (
                    f"Daily audit limit of {self.max_per_day} reached. "
                    "Please try again tomorrow."
                )
            cutoff = now - 60
            while self._minute_window and self._minute_window[0] < cutoff:
                self._minute_window.popleft()
            if len(self._minute_window) >= self.max_per_minute:
                wait = int(60 - (now - self._minute_window[0])) + 1
                return False, (
                    f"Rate limit: max {self.max_per_minute} audits per minute. "
                    f"Try again in ~{wait}s."
                )
            self._minute_window.append(now)
            self._day_count += 1
            return True, ""


_rate_limiter = _RateLimiter()

# CFR parts: key (frontend) -> (label, fetcher). Fetched at startup for reversed RAG.
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

_llm = None
_REGULATION_TEXTS: dict[str, str] = {}  # label -> full text, populated at startup


@app.on_event("startup")
async def startup():
    global _llm, _REGULATION_TEXTS
    if os.environ.get("GEMINI_API_KEY", "").strip():
        logger.info("Loading LLM (Gemini 1.5 Flash)...")
        _llm = GeminiFlashLLM(temperature=0.1, max_tokens=4096)
    else:
        logger.info("Loading LLM (Vertex AI MedGemma)...")
        _llm = MedGemmaVertexLLM(
            project=os.environ["GCP_PROJECT_ID"],
            location=os.environ.get("GCP_REGION", "europe-west4"),
            endpoint_id=os.environ["VERTEX_ENDPOINT_ID"],
            temperature=0.1,
            max_tokens=4096,
        )

    logger.info("Fetching eCFR regulations (for per-regulation protocol check)...")
    for key, (label, fetcher) in REGULATION_MAP.items():
        try:
            raw = fetcher()
            _REGULATION_TEXTS[label] = raw
            logger.info("  ✓ %s", label)
        except Exception as e:
            logger.warning("  ✗ %s: %s", label, e)

    # Warm embeddings model (used when protocol is uploaded); respects EMBEDDING_MODEL env
    get_embeddings()
    emb_choice = os.environ.get("EMBEDDING_MODEL", "").strip().lower() or "huggingface"
    logger.info(
        "CLARA API ready. Reversed RAG: protocols chunked and embedded on upload; "
        "each CFR regulation checked against protocol index. Embeddings: %s.",
        "medsiglip" if emb_choice in ("medsiglip", "siglip") else "sentence-transformers",
    )


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
You are an FDA auditor. The knowledge base is ONLY the UPLOADED PROTOCOL (chunked and embedded). Each CFR regulation was checked against this protocol index: the regulation text was used as the query to retrieve protocol chunks that match. Below, for each regulation you are given: (1) an excerpt of the regulation text, and (2) either the protocol chunks that were found to address it, or "(No matching protocol sections found for this regulation.)". The knowledge consists only of those protocol chunks; regulations are not in the knowledge base.

CRITICAL RULE: For any regulation where the protocol sections say "(No matching protocol sections found for this regulation.)", you MUST set status to "critical" (or at least "warning"). Include in gaps: "Protocol does not address this regulation" and in remediation suggest adding protocol sections that cover this regulation.

REGULATORY CONTEXT (each regulation with the protocol chunks that address it, or no match):
{context}

FULL PROTOCOL (excerpt for reference):
{protocol}

REGULATIONS TO AUDIT (you must output exactly one object per regulation below):
{regulations}

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


def _ensure_all_regulations_in_breakdown(
    breakdown: list[dict],
    reg_labels: list[str],
    regulation_to_chunks: dict[str, list[str]],
) -> list[dict]:
    """
    Ensure the breakdown contains exactly one entry per regulation. If the LLM
    omitted a regulation, add it: use critical when no protocol chunks matched,
    otherwise warning.
    """
    by_reg = {item.get("regulation", "").strip(): item for item in breakdown}
    result = []
    for label in reg_labels:
        if label in by_reg:
            result.append(by_reg[label])
        else:
            has_chunks = bool(regulation_to_chunks.get(label))
            result.append({
                "regulation": label,
                "status": "critical" if not has_chunks else "warning",
                "note": "Protocol does not address this regulation." if not has_chunks else "No audit finding returned; review manually.",
                "focus": "Coverage in protocol",
                "gaps": ["No matching protocol sections."] if not has_chunks else ["Audit output missing for this regulation."],
                "remediation": ["Add protocol sections that address this regulation."] if not has_chunks else ["Re-run audit or review protocol for this regulation."],
            })
            logger.info("Backfilled missing breakdown for %s (no_match=%s)", label, not has_chunks)
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
    """Upload a protocol PDF; chunk and embed it, then check each CFR regulation against the protocol and run the audit."""
    if _llm is None or not _REGULATION_TEXTS:
        raise HTTPException(503, "Pipeline not initialized yet — server is still starting up.")

    # Rate limit check
    ok, msg = _rate_limiter.check()
    if not ok:
        raise HTTPException(429, msg)

    # 1. Extract text
    contents = await file.read()
    if len(contents) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            413,
            f"File too large — maximum {_MAX_UPLOAD_BYTES // (1024 * 1024)} MB.",
        )
    if file.filename and file.filename.lower().endswith(".pdf"):
        protocol_text = extract_text_from_pdf(contents)
    else:
        protocol_text = contents.decode("utf-8", errors="replace")

    if not protocol_text.strip():
        raise HTTPException(400, "Could not extract any text from the uploaded file.")

    # 2. Use only the regulations selected on the frontend (comma-separated keys)
    if regulations and regulations.strip():
        reg_keys = [k.strip() for k in regulations.split(",")]
    else:
        reg_keys = list(REGULATION_MAP.keys())
    reg_labels = [
        REGULATION_MAP[k][0] for k in reg_keys
        if k in REGULATION_MAP and REGULATION_MAP[k][0] in _REGULATION_TEXTS
    ]
    if not reg_labels:
        raise HTTPException(400, "No valid regulations selected or loaded.")
    regulations_text = ", ".join(reg_labels)

    # 3. Index the uploaded protocol (chunk + embed) so we can query by regulation
    logger.info("Chunking and embedding uploaded protocol...")
    protocol_vector_db = index_protocol(protocol_text)

    # 4. For each CFR regulation, query the protocol index to find which protocol sections address it
    logger.info("Checking each selected CFR regulation against the protocol...")
    regulation_to_chunks: dict[str, list[str]] = {}
    retrieved_sections = []

    for label in reg_labels:
        reg_text = _REGULATION_TEXTS.get(label, "")
        if not reg_text:
            continue
        chunks = query_protocol_for_regulation(protocol_vector_db, reg_text, k=5)
        regulation_to_chunks[label] = chunks
        for c in chunks:
            snippet = (c[:80].replace("\n", " ") + "...") if len(c) > 80 else c.replace("\n", " ")
            retrieved_sections.append(f"[{label}] {snippet}")

    # Build context: for each regulation, show regulation text + protocol excerpts that address it
    context_parts = []
    for label in reg_labels:
        reg_text = _REGULATION_TEXTS.get(label, "")
        chunks = regulation_to_chunks.get(label, [])
        # Truncate regulation for context window; include all retrieved protocol chunks for this reg
        reg_excerpt = (reg_text[:3500] + "...") if len(reg_text) > 3500 else reg_text
        protocol_excerpts = "\n\n".join(chunks) if chunks else "(No matching protocol sections found for this regulation.)"
        context_parts.append(
            f"### {label}\n\n**Regulation (excerpt):**\n{reg_excerpt}\n\n**Protocol sections addressing this regulation:**\n{protocol_excerpts}"
        )
    context = "\n\n---\n\n".join(context_parts)
    logger.info("Built context for %d regulations with protocol-matched sections", len(reg_labels))

    # 5. Audit step — use structured prompt (context = per-regulation + protocol sections that address it)
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

    # 4c. Ensure every regulation has an entry; backfill missing as critical
    breakdown = _ensure_all_regulations_in_breakdown(breakdown, reg_labels, regulation_to_chunks)

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
            f"RAG: protocol \"{title or file.filename}\" was chunked and embedded as the knowledge base. "
            f"Each CFR regulation ({regulations_text}) was checked against the protocol index; "
            f"retrieved protocol sections were used for the audit."
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
        "pipeline_ready": _llm is not None and len(_REGULATION_TEXTS) > 0,
        "audits_count": len(_audits),
    }
