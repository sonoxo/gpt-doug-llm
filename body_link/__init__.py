"""Authenticated GPT-Doug remote-body link."""

from .client import BodyLinkClient, BodyLinkError
from .protocol import normalize_runtime_url

__all__ = ["BodyLinkClient", "BodyLinkError", "normalize_runtime_url"]
