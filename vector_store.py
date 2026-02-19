import os
import re
import shutil
import logging

from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

logger = logging.getLogger(__name__)

CHROMA_DIR = "./data/chroma_db"

# Regex to detect the CFR part header injected during startup
_CFR_HEADER_RE = re.compile(r"<!--\s*(.*?)\s*-->")


def initialize_rag(raw_law_text: str):
    """Build (or rebuild) a ChromaDB vector store from CFR regulation text.

    Each chunk is tagged with ``cfr_part`` metadata (e.g. "21 CFR Part 50")
    so retrieval can be scoped to only the regulations the user selected.
    Returns the underlying Chroma vector_db (not a retriever) so callers
    can apply metadata filters at query time.
    """
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    # Wipe and rebuild on every startup so we always reflect fresh eCFR data
    if os.path.exists(CHROMA_DIR):
        shutil.rmtree(CHROMA_DIR)
        logger.info("Cleared stale ChromaDB at %s", CHROMA_DIR)

    # ── Split each CFR part separately so we can tag metadata ──
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=120,
        separators=["\n\n", "\n", " "],
    )

    # Split the combined text on the HTML-comment headers first
    parts = re.split(r"(\n\n<!-- .+? -->\n)", raw_law_text)

    docs: list[Document] = []
    current_label = "Unknown"

    for segment in parts:
        segment = segment.strip()
        if not segment:
            continue

        # Check if this segment is a header like <!-- 21 CFR Part 50 -->
        header_match = _CFR_HEADER_RE.search(segment)
        if header_match and len(segment) < 80:
            current_label = header_match.group(1)
            continue

        # Otherwise it's regulation body text — chunk it
        chunks = splitter.split_text(segment)
        for chunk in chunks:
            docs.append(Document(
                page_content=chunk,
                metadata={"cfr_part": current_label},
            ))

    logger.info("Split regulation text into %d chunks across CFR parts", len(docs))

    # Log distribution
    from collections import Counter
    dist = Counter(d.metadata["cfr_part"] for d in docs)
    for part, count in dist.most_common():
        logger.info("  %s: %d chunks", part, count)

    vector_db = Chroma.from_documents(
        docs, embeddings, persist_directory=CHROMA_DIR
    )

    return vector_db