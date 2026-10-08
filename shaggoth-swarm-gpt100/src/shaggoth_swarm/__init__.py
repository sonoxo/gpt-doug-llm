"""Shaggoth Swarm GPT-100."""

from .broker import CapabilityBroker
from .config import SwarmConfig
from .orchestrator import SwarmOrchestrator
from .policy import CapabilityPolicy

__all__ = ["CapabilityBroker", "CapabilityPolicy", "SwarmConfig", "SwarmOrchestrator"]
__version__ = "0.3.0"
