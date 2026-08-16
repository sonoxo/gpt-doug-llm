from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


class Evidence(BaseModel):
    id: str = Field(default_factory=lambda: new_id("ev"))
    source_type: str
    citation: Optional[str] = None
    note: Optional[str] = None
    url: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)


class Entity(BaseModel):
    id: str = Field(default_factory=lambda: new_id("ent"))
    type: str
    name: str
    aliases: List[str] = Field(default_factory=list)
    jurisdiction: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)
    evidence: List[Evidence] = Field(default_factory=list)


class Relation(BaseModel):
    id: str = Field(default_factory=lambda: new_id("rel"))
    source: str
    target: str
    type: str
    confidence: str = "confirmed"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)
    evidence: List[Evidence] = Field(default_factory=list)
