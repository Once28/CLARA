"""
Reversed RAG: uploaded protocols are the knowledge base (chunked and embedded).
CFR regulations are used as queries to find which protocol sections address each regulation.
"""

import os
import logging
from transformers import AutoModel, AutoTokenizer
from typing import List

import torch
from langchain_core.embeddings import Embeddings
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings  # kept for optional swap
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

logger = logging.getLogger(__name__)


# ─── MedSigLIP / SigLIP text-encoder wrapper ──────────────────
# Set EMBEDDING_MODEL=medsiglip to use this. MedSigLIP/SigLIP are
# vision-language models; the text encoder is used for text↔text retrieval
# here (experimental). For production RAG, sentence-transformers usually give
# better recall.

class MedSigLIPTextEmbeddings(Embeddings):
    """LangChain Embeddings wrapper around SigLIP/MedSigLIP text encoder."""

    def __init__(self, model_name: str = "google/siglip-base-patch16-224"):
        from transformers import SiglipProcessor, SiglipModel

        self.processor = SiglipProcessor.from_pretrained(model_name)
        self.model = SiglipModel.from_pretrained(model_name)
        self.model.eval()
        self._max_length = min(
            getattr(self.processor.tokenizer, "model_max_length", 64),
            64,
        )
        logger.info("Loaded SigLIP/MedSigLIP text encoder: %s (max_length=%d)", model_name, self._max_length)

    def _embed(self, texts: List[str]) -> List[List[float]]:
        """Tokenize and encode a batch of texts, return L2-normalised vectors."""
        # Processor returns input_ids, attention_mask; for text-only no pixel_values
        inputs = self.processor(
            text=texts,
            padding="max_length",
            truncation=True,
            max_length=self._max_length,
            return_tensors="pt",
        )
        # SiglipModel accepts input_ids, attention_mask; pixel_values optional
        with torch.no_grad():
            outputs = self.model(
                input_ids=inputs["input_ids"],
                attention_mask=inputs.get("attention_mask"),
            )

        if hasattr(outputs, "text_embeds") and outputs.text_embeds is not None:
            embeds = outputs.text_embeds
        elif hasattr(outputs, "pooler_output"):
            embeds = outputs.pooler_output
        else:
            embeds = outputs.last_hidden_state[:, 0, :]

        embeddings = torch.nn.functional.normalize(embeds, dim=-1)
        return embeddings.cpu().tolist()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        batch_size = 32
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

# Env: "medsiglip" | "siglip" => MedSigLIPTextEmbeddings; else HuggingFace (default)
EMBEDDING_MODEL_ENV = "EMBEDDING_MODEL"
MEDSIGLIP_MODEL_ENV = "MEDSIGLIP_MODEL_NAME"  # e.g. google/siglip-base-patch16-224


def get_embeddings(force_reset: bool = False):
    """
    Return the shared embeddings instance. Choice is driven by env EMBEDDING_MODEL:
    - "medsiglip" or "siglip" => MedSigLIPTextEmbeddings (SigLIP text encoder)
    - else => HuggingFaceEmbeddings (sentence-transformers/all-MiniLM-L6-v2)
    """
    global _embeddings
    if force_reset:
        _embeddings = None
    if _embeddings is None:
        choice = (os.environ.get(EMBEDDING_MODEL_ENV) or "").strip().lower()
        if choice in ("medsiglip", "siglip"):
            model_name = os.environ.get(MEDSIGLIP_MODEL_ENV, "google/siglip-base-patch16-224")
            _embeddings = MedSigLIPTextEmbeddings(model_name=model_name)
            logger.info("Using MedSigLIP/SigLIP embeddings: %s", model_name)
        else:
            _embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2"
            )
            logger.info("Using HuggingFace embeddings: sentence-transformers/all-MiniLM-L6-v2")
    return _embeddings


def get_protocol_splitter():
    """Text splitter for protocol documents."""
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
