"""
ResearchMind AI – Pydantic Schemas (Request / Response DTOs)
"""
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ─────────────────────────────────────────────────────────────────────────────
#  Project Schemas
# ─────────────────────────────────────────────────────────────────────────────
class ProjectCreate(BaseModel):
    topic: str = Field(..., min_length=3, max_length=512, examples=["Impact of AI in Healthcare"])


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    topic: str
    subtopics: Optional[List[str]] = None
    research_questions: Optional[List[str]] = None
    status: str
    confidence_score: Optional[float] = None
    created_at: datetime
    updated_at: datetime


class ProjectDetailResponse(ProjectResponse):
    sources_count: int = 0
    contradictions_count: int = 0
    gaps_count: int = 0


# ─────────────────────────────────────────────────────────────────────────────
#  Source Schemas
# ─────────────────────────────────────────────────────────────────────────────
class SourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    url: Optional[str] = None
    source_type: str
    reliability_score: Optional[float] = None
    justification: Optional[str] = None
    fetched_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
#  Contradiction Schemas
# ─────────────────────────────────────────────────────────────────────────────
class ContradictionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    claim_a: str
    source_a_id: Optional[uuid.UUID] = None
    claim_b: str
    source_b_id: Optional[uuid.UUID] = None
    explanation: Optional[str] = None
    resolution_tip: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
#  Research Gap Schemas
# ─────────────────────────────────────────────────────────────────────────────
class ResearchGapResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    gap_title: str
    description: Optional[str] = None
    evidence: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
#  Report Schemas
# ─────────────────────────────────────────────────────────────────────────────
class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    markdown_content: Optional[str] = None
    citations: Optional[Dict[str, Any]] = None
    pptx_file_path: Optional[str] = None
    created_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
#  Agent / WebSocket Event Schemas
# ─────────────────────────────────────────────────────────────────────────────
class AgentStatusEvent(BaseModel):
    """Sent over WebSocket to update the UI on which agent is active."""
    project_id: str
    agent: str          # planner | researcher | critic | writer | reviewer
    status: str         # started | completed | failed
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


# ─────────────────────────────────────────────────────────────────────────────
#  Generic Responses
# ─────────────────────────────────────────────────────────────────────────────
class MessageResponse(BaseModel):
    message: str


class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None
