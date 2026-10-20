"""GPT-Doug universal watchdog for explicitly integrated AI runtimes."""

__version__ = "1.0.0"
from .core import Watchtower
from .policy import PolicyError

__all__ = ["Watchtower", "PolicyError"]
