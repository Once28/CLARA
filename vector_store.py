"""
Reversed RAG: uploaded protocols are the knowledge base (chunked and embedded).
CFR regulations are used as queries to find which protocol sections address each regulation.
"""

import os
import logging

from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

logger = logging.getLogger(__name__)

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
