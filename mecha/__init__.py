"""Monorepo-only import shim for the portable mecha/mecha package.

Standalone installations resolve the inner mecha package directly; this shim
lets a whole-repository test runner import the same code without PYTHONPATH edits.
"""
from pathlib import Path

__path__ = [str(Path(__file__).parent / 'mecha')]
