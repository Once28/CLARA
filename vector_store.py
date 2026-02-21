import os
import re
import shutil
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

# Regex to detect the CFR part header injected during startup
_CFR_HEADER_RE = re.compile(r"<!--\s*(.*?)\s*-->")


def initialize_rag(raw_law_text: str):
    """Build (or rebuild) a ChromaDB vector store from CFR regulation text.

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