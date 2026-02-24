"""
Gemini 1.5 Flash placeholder LLM — drop-in replacement for MedGemmaVertexLLM
during development and demos when VERTEX_ENDPOINT_ID is not available.

Set GEMINI_API_KEY in backend/.env to activate.
"""

import os
import logging

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)


class GeminiFlashLLM:
    """
    Thin wrapper around Gemini 1.5 Flash with the same invoke(prompt) -> str
    interface as MedGemmaVertexLLM.
    """

    def __init__(
        self,
        model: str = "gemini-1.5-flash",
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ):
        api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not api_key:
            raise ValueError("GEMINI_API_KEY must be set in backend/.env")
        self._llm = ChatGoogleGenerativeAI(
            model=model,
            temperature=temperature,
            max_output_tokens=max_tokens,
            google_api_key=api_key,
        )
        logger.info("GeminiFlashLLM ready (model: %s)", model)

    def invoke(self, prompt: str) -> str:
        response = self._llm.invoke([HumanMessage(content=prompt)])
        return response.content
