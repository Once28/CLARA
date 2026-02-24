"""
Reversed RAG: uploaded protocols are the knowledge base (chunked and embedded).
CFR regulations are used as queries to find which protocol sections address each regulation.
"""

import os
import logging
from pathlib import Path
from typing import List

import torch
from transformers import AutoModel, AutoTokenizer
from langchain_core.embeddings import Embeddings
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings  # kept for optional swap
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

logger = logging.getLogger(__name__)


# ─── MedSigLIP text-encoder wrapper ──────────────────────────
# NOTE: MedSigLIP is a contrastive vision-language model. Its text encoder
# is optimised for image↔text alignment, NOT text↔text retrieval. Using it
# here is experimental; a dedicated sentence-embedding model (see commented-
# out option below) will generally produce better RAG recall.

def _hf_login_if_configured():
    """Authenticate to HuggingFace Hub if HF_TOKEN is set (needed for gated models like MedSigLIP)."""
    token = os.environ.get("HF_TOKEN", "").strip()
    if token:
        try:
            from huggingface_hub import login
            login(token=token, add_to_git_credential=False)
            logger.info("Authenticated with HuggingFace Hub (HF_TOKEN found)")
        except Exception as e:
            logger.warning("HuggingFace login failed: %s", e)


class MedSigLIPTextEmbeddings(Embeddings):
    """LangChain Embeddings wrapper around MedSigLIP's text encoder.

    Tries the real MedSigLIP checkpoint first (requires HF gated access +
    HF_TOKEN env var). Falls back to the public SigLIP-base proxy if the
    gated model is unavailable.
    """

    _REAL_CHECKPOINT = "google/medsiglip-base-patch16-256"
    _PROXY_CHECKPOINT = "google/siglip-base-patch16-256"

    def __init__(self, model_name: str = None):
        _hf_login_if_configured()

        if model_name is None:
            # Try the real MedSigLIP checkpoint; fall back to SigLIP if not accessible.
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(self._REAL_CHECKPOINT)
                self.model = AutoModel.from_pretrained(self._REAL_CHECKPOINT)
                model_name = self._REAL_CHECKPOINT
            except Exception:
                logger.warning(
                    "MedSigLIP checkpoint '%s' not accessible — falling back to SigLIP proxy. "
                    "Set HF_TOKEN and request gated access at huggingface.co/%s to use the real model.",
                    self._REAL_CHECKPOINT,
                    self._REAL_CHECKPOINT,
                )
                self.tokenizer = AutoTokenizer.from_pretrained(self._PROXY_CHECKPOINT)
                self.model = AutoModel.from_pretrained(self._PROXY_CHECKPOINT)
                model_name = self._PROXY_CHECKPOINT
        else:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModel.from_pretrained(model_name)

        self.model.eval()
        logger.info("Loaded MedSigLIP text encoder: %s", model_name)

    def _embed(self, texts: List[str]) -> List[List[float]]:
        """Tokenize and encode a batch of texts, returning L2-normalised vectors."""
        inputs = self.tokenizer(
            texts,
            padding="max_length",
            truncation=True,
            max_length=64,  # SigLIP-base max_position_embeddings = 64 tokens
            return_tensors="pt",
        )
        with torch.no_grad():
            outputs = self.model.get_text_features(**inputs)  # (batch, dim)
        # L2-normalise so cosine similarity = dot product (Chroma default)
        embeddings = torch.nn.functional.normalize(outputs, dim=-1)
        return embeddings.cpu().tolist()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        # Batch to avoid OOM — SigLIP base is ~813 MB
        batch_size = 64
        all_embeddings: List[List[float]] = []
        for i in range(0, len(texts), batch_size):
            all_embeddings.extend(self._embed(texts[i : i + batch_size]))
        return all_embeddings

    def embed_query(self, text: str) -> List[float]:
        return self._embed([text])[0]

class MedSigLIPVertexEmbeddings(Embeddings):
    """
    MedSigLIP text embeddings via a Vertex AI Model Garden endpoint.

    Deploy MedSigLIP from Model Garden, copy the endpoint ID into
    MEDSIGLIP_ENDPOINT_ID, and this class will be used automatically
    instead of the HuggingFace path.
    """

    def __init__(self):
        from google.cloud import aiplatform as _aip
        project = os.environ.get("GCP_PROJECT_ID", "")
        endpoint_id = os.environ.get("MEDSIGLIP_ENDPOINT_ID", "")
        # Use endpoint-specific region (may differ from the MedGemma region)
        region = os.environ.get("MEDSIGLIP_ENDPOINT_REGION") or os.environ.get("GCP_REGION", "europe-west4")
        if not project or not endpoint_id:
            raise ValueError("GCP_PROJECT_ID and MEDSIGLIP_ENDPOINT_ID must be set")
        _aip.init(project=project, location=region)
        # Full resource name ensures the SDK routes to the correct region
        # regardless of what aiplatform.init() was called with globally.
        resource_name = f"projects/{project}/locations/{region}/endpoints/{endpoint_id}"
        self._endpoint = _aip.Endpoint(resource_name)
        logger.info("MedSigLIP Vertex endpoint ready: %s (%s)", endpoint_id, region)

    @staticmethod
    def _extract_vector(pred) -> list[float]:
        """Handle the two common Vertex embedding response shapes."""
        if isinstance(pred, list):
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
        batch_size = 32
        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            instances = [{"text": t} for t in batch]
            response = self._endpoint.predict(instances=instances)
            all_embeddings.extend(
                self._extract_vector(p) for p in response.predictions
            )
        return all_embeddings

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


CHROMA_DIR = str(Path(__file__).parent.parent / "data" / "chroma_db")
PROTOCOL_COLLECTION = "protocol_chunks"

# Lazy singleton for embeddings (shared for protocol indexing and CFR-as-query)
_embeddings = None


def _using_medsiglip() -> bool:
    """True when MedSigLIP is the active embedding model (Vertex or HuggingFace path)."""
    return bool(os.environ.get("MEDSIGLIP_ENDPOINT_ID", "").strip()) or \
           os.environ.get("EMBEDDING_MODEL", "").strip().lower() in ("medsiglip", "siglip")


def get_embeddings():
    """Return the active embeddings model.

    Priority order:
      1. MEDSIGLIP_ENDPOINT_ID set  → MedSigLIPVertexEmbeddings (Model Garden endpoint)
      2. EMBEDDING_MODEL=medsiglip  → MedSigLIPTextEmbeddings (HuggingFace, real or proxy)
      3. default                    → sentence-transformers/all-MiniLM-L6-v2
    """
    global _embeddings
    if _embeddings is None:
        if os.environ.get("MEDSIGLIP_ENDPOINT_ID", "").strip():
            _embeddings = MedSigLIPVertexEmbeddings()
        elif os.environ.get("EMBEDDING_MODEL", "").strip().lower() in ("medsiglip", "siglip"):
            _embeddings = MedSigLIPTextEmbeddings()
        else:
            _embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2"
            )
    return _embeddings


def get_protocol_splitter():
    """Text splitter for protocol documents.

    Uses 300-char chunks for MedSigLIP (SigLIP-base 64-token max ≈ 300 chars)
    and 800-char chunks for MiniLM so neither model silently truncates chunks.
    """
    if _using_medsiglip():
        return RecursiveCharacterTextSplitter(
            chunk_size=300,
            chunk_overlap=50,
            separators=["\n\n", "\n", ". ", " "],
        )
    return RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=120,
        separators=["\n\n", "\n", ". ", " "],
    )


def index_protocol(protocol_text: str, persist_directory: str = CHROMA_DIR):
    """
    Chunk the uploaded protocol, embed chunks, and store them in Chroma.

    The protocol becomes the knowledge base. Each CFR regulation is later
    checked against this index (regulation text as query) to find which
    protocol sections address it.

    Uses collection PROTOCOL_COLLECTION; each new upload overwrites the
    previous protocol index (one protocol at a time).
    """
    if not protocol_text or not protocol_text.strip():
        raise ValueError("protocol_text must be non-empty")

    embeddings = get_embeddings()
    splitter = get_protocol_splitter()
    chunks = splitter.split_text(protocol_text.strip())

    docs = [
        Document(page_content=chunk, metadata={"source": "uploaded_protocol"})
        for chunk in chunks
    ]
    logger.info("Split protocol into %d chunks for embedding", len(docs))

    vector_db = Chroma.from_documents(
        docs,
        embeddings,
        collection_name=PROTOCOL_COLLECTION,
        persist_directory=persist_directory,
    )
    return vector_db


def get_protocol_retriever(protocol_vector_db, k: int = 5, fetch_k: int = 20):
    """
    Return a retriever over the indexed protocol. CFR regulation text is used
    as the query to find which protocol chunks address that regulation.
    """
    return protocol_vector_db.as_retriever(
        search_type="mmr",
        search_kwargs={"k": k, "fetch_k": fetch_k, "lambda_mult": 0.5},
    )


def query_protocol_for_regulation(protocol_vector_db, regulation_text: str, k: int = 5):
    """
    Check if a CFR regulation is addressed in the uploaded protocol: use the
    regulation text as the query against the protocol index and return the
    most relevant protocol chunks.

    Returns list of protocol chunk strings (page_content).
    """
    query = regulation_text[:4000].strip() if regulation_text else ""
    if not query:
        return []

    retriever = get_protocol_retriever(protocol_vector_db, k=k)
    docs = retriever.invoke(query)
    return [d.page_content for d in docs]
