"""
Custom LangChain LLM wrapper for MedGemma 1.5 4B-IT deployed on a
Vertex AI Endpoint (Model Garden one-click deploy with vLLM serving).

The endpoint expects the chat-completions format wrapped in `instances`:

    {
        "instances": [{
            "@requestFormat": "chatCompletions",
            "messages": [...],
            "max_tokens": 4096
        }]
    }

Deployment details:
    Model:    google/medgemma-1.5-4b-it  (vLLM 128K context)
    Endpoint: google_medgemma-1_5-4b-it-mg-one-click-deploy
    Region:   europe-west4
    GPU:      NVIDIA_RTX_PRO_6000 x1
"""

import ast
import json
import os
import logging
import re
from typing import Any, Optional

from langchain_core.language_models.llms import LLM
from google.cloud import aiplatform

logger = logging.getLogger(__name__)

# System prompt injected into every MedGemma call
_SYSTEM_PROMPT = (
    "You are a Senior FDA Regulatory Auditor and clinical research expert. "
    "You provide precise, evidence-based analysis of clinical protocols "
    "against 21 CFR and 45 CFR regulations."
)


class MedGemmaVertexLLM(LLM):
    """LangChain LLM that calls a MedGemma endpoint on Vertex AI."""

    project: str = ""
    location: str = "europe-west4"
    endpoint_id: str = ""
    max_tokens: int = 4096
    temperature: float = 0.1
    system_prompt: str = _SYSTEM_PROMPT

    _endpoint: Any = None  # lazy-initialised aiplatform.Endpoint

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Fill from env vars if not explicitly provided
        self.project = self.project or os.environ.get("GCP_PROJECT_ID", "")
        self.location = self.location or os.environ.get("GCP_REGION", "europe-west4")
        self.endpoint_id = self.endpoint_id or os.environ.get("VERTEX_ENDPOINT_ID", "")

        if not self.project:
            raise ValueError("GCP_PROJECT_ID must be set (env var or constructor arg)")
        if not self.endpoint_id:
            raise ValueError("VERTEX_ENDPOINT_ID must be set (env var or constructor arg)")

        # Initialise the Vertex AI SDK once
        aiplatform.init(project=self.project, location=self.location)
        self._endpoint = aiplatform.Endpoint(self.endpoint_id)
        logger.info(
            "MedGemma endpoint ready  project=%s  region=%s  endpoint=%s",
            self.project, self.location, self.endpoint_id,
        )

    @property
    def _llm_type(self) -> str:
        return "medgemma-vertex"

    def _call(
        self,
        prompt: str,
        stop: Optional[list[str]] = None,
        **kwargs,
    ) -> str:
        """Send a prompt to the MedGemma endpoint and return the text."""
        messages = []

        # Add system message for regulatory context
        if self.system_prompt:
            messages.append({
                "role": "system",
                "content": [{"type": "text", "text": self.system_prompt}],
            })

        # Add user prompt
        messages.append({
            "role": "user",
            "content": [{"type": "text", "text": prompt}],
        })

        instance = {
            "@requestFormat": "chatCompletions",
            "messages": messages,
            "max_tokens": self.max_tokens,
        }

        logger.debug("Sending %d-char prompt to MedGemma endpoint", len(prompt))
        response = self._endpoint.predict(instances=[instance])

        # Parse the response – Vertex AI returns predictions as a list
        return self._parse_response(response)

    @staticmethod
    def _extract_content_from_dict(d: dict) -> Optional[str]:
        """Dig into a chat-completions-style dict and pull out the text."""
        # Layout: {"choices": [{"message": {"content": "..."}}]}
        choices = d.get("choices", [])
        if choices and isinstance(choices, list):
            msg = choices[0]
            if isinstance(msg, dict):
                content = (
                    msg.get("message", {}).get("content")
                    or msg.get("text")
                    or msg.get("content")
                )
                if content:
                    return str(content)

        # Direct top-level keys
        for key in ("content", "output", "text", "generated_text", "response"):
            if key in d:
                return str(d[key])
        return None

    @staticmethod
    def _try_parse_as_dict(s: str) -> Optional[dict]:
        """Try to interpret a string as a Python dict or JSON object."""
        # Try JSON first
        try:
            obj = json.loads(s)
            if isinstance(obj, dict):
                return obj
        except (json.JSONDecodeError, ValueError):
            pass
        # Try Python literal (handles single-quoted dicts, None vs null, etc.)
        try:
            obj = ast.literal_eval(s)
            if isinstance(obj, dict):
                return obj
        except (ValueError, SyntaxError):
            pass
        return None

    @classmethod
    def _parse_response(cls, response) -> str:
        """
        Extract the assistant text from the Vertex AI endpoint response.

        vLLM on Vertex AI returns predictions in different shapes depending
        on the serving container version:
          - A dict (the chat-completions object itself)
          - A list containing one dict
          - A list containing a string
        """
        try:
            predictions = response.predictions
            logger.info("Raw predictions type=%s  count=%d",
                        type(predictions).__name__,
                        len(predictions) if predictions else 0)

            if not predictions:
                return "[MedGemma returned no predictions]"

            # ── predictions is directly a chat-completions dict ──
            if isinstance(predictions, dict):
                text = cls._extract_content_from_dict(predictions)
                if text:
                    logger.info("Extracted content from predictions dict (%d chars)", len(text))
                    return text

            # ── predictions is a list ──
            if isinstance(predictions, list):
                pred = predictions[0]

                if isinstance(pred, dict):
                    text = cls._extract_content_from_dict(pred)
                    if text:
                        logger.info("Extracted content from predictions[0] dict (%d chars)", len(text))
                        return text

                if isinstance(pred, str):
                    parsed = cls._try_parse_as_dict(pred)
                    if parsed:
                        text = cls._extract_content_from_dict(parsed)
                        if text:
                            logger.info("Extracted content from parsed string (%d chars)", len(text))
                            return text
                    return pred

            # ── Fallback: stringify whatever we got ──
            text = str(predictions)
            logger.warning("Could not extract content; returning str(predictions) (%d chars)", len(text))
            return text

        except Exception as e:
            logger.error("Failed to parse MedGemma response: %s  (type: %s)", e, type(e).__name__)
            try:
                return str(response.predictions)
            except Exception:
                return f"[Error parsing MedGemma response: {e}]"
