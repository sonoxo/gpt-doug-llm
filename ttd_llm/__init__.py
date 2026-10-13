"""GPT-Doug TTD-LLM: evidence-backed Talk-to-Data."""

from .engine import DataCatalog, TTDValidationError
from .ollama import LocalModelError, Ollama

__all__ = ["DataCatalog", "TTDValidationError", "LocalModelError", "Ollama"]
