"""Shaggoth Swarm GPT-100."""

from .atomic import AtomicEnvelope, AtomicLayer
from .broker import CapabilityBroker
from .config import SwarmConfig
from .orchestrator import SwarmOrchestrator
from .policy import CapabilityPolicy

__all__ = [
    "AtomicEnvelope",
    "AtomicLayer",
    "CapabilityBroker",
    "CapabilityPolicy",
    "SwarmConfig",
    "SwarmOrchestrator",
]
__version__ = "0.3.0"
