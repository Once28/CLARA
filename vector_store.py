"""
Reversed RAG: uploaded protocols are the knowledge base (chunked and embedded).
CFR regulations are used as queries to find which protocol sections address each regulation.
"""

import os
import logging
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

class MedSigLIPTextEmbeddings(Embeddings):
    """LangChain Embeddings wrapper around MedSigLIP's text encoder."""

    def __init__(self, model_name: str = "google/siglip-base-patch16-256"):
        # MedSigLIP shares the SigLIP architecture; swap model_name to the
        # specific MedSigLIP checkpoint once you have gated access, e.g.
        #   "google/medsiglip-base-patch16-256"
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

CHROMA_DIR = "./data/chroma_db"
PROTOCOL_COLLECTION = "protocol_chunks"

# Lazy singleton for embeddings (shared for protocol indexing and CFR-as-query)
_embeddings = None


def get_embeddings():
    """Shared HuggingFace embeddings for protocol chunks (KB) and CFR-as-query retrieval."""
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
    return _embeddings

<<<<<<< HEAD
    Each chunk is tagged with ``cfr_part`` metadata (e.g. "21 CFR Part 50")
    so retrieval can be scoped to only the regulations the user selected.
    Returns the underlying Chroma vector_db (not a retriever) so callers
    can apply metadata filters at query time.
    """
    # ── Choose embedding model ──────────────────────────────
    # Option A: MedSigLIP text encoder (experimental, HAI-DEF)
    embeddings = MedSigLIPTextEmbeddings(
        model_name="google/siglip-base-patch16-256",
        # Switch to the gated MedSigLIP checkpoint when available:
        # model_name="google/medsiglip-base-patch16-256",
    )

    # Option B: General-purpose sentence embeddings (better for text↔text RAG)
    # embeddings = HuggingFaceEmbeddings(
    #     model_name="sentence-transformers/all-MiniLM-L6-v2"
    # )

    # Wipe and rebuild on every startup so we always reflect fresh eCFR data
    if os.path.exists(CHROMA_DIR):
        shutil.rmtree(CHROMA_DIR)
        logger.info("Cleared stale ChromaDB at %s", CHROMA_DIR)

    # ── Split each CFR part separately so we can tag metadata ──
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
=======

def get_protocol_splitter():
    """Text splitter for protocol documents."""
    return RecursiveCharacterTextSplitter(
        chunk_size=800,
>>>>>>> 5fb04a88e034502960c9660582cb3601462e2bc9
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
