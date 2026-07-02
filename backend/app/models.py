"""
ResearchMind AI – ORM Models
All tables are defined here and registered with Alembic via the Base metadata.
"""
import uuid
from datetime import datetime
from typing import List, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.config import get_settings

settings = get_settings()


# ─────────────────────────────────────────────────────────────────────────────
#  Project – top-level research session
# ─────────────────────────────────────────────────────────────────────────────
class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    topic: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    subtopics: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    research_questions: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(
        String(64), nullable=False, default="pending", index=True
    )
    # pending | planning | researching | critiquing | writing | reviewing | done | failed
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # relationships
    sources: Mapped[List["Source"]] = relationship(
        "Source", back_populates="project", cascade="all, delete-orphan"
    )
    contradictions: Mapped[List["Contradiction"]] = relationship(
        "Contradiction", back_populates="project", cascade="all, delete-orphan"
    )
    research_gaps: Mapped[List["ResearchGap"]] = relationship(
        "ResearchGap", back_populates="project", cascade="all, delete-orphan"
    )
    report: Mapped[Optional["Report"]] = relationship(
        "Report", back_populates="project", uselist=False, cascade="all, delete-orphan"
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Source – a web page, research paper, or uploaded PDF
# ─────────────────────────────────────────────────────────────────────────────
class Source(Base):
    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="web"
    )  # pdf | paper | web | news
    reliability_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    justification: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    project: Mapped["Project"] = relationship("Project", back_populates="sources")
    chunks: Mapped[List["DocumentChunk"]] = relationship(
        "DocumentChunk", back_populates="source", cascade="all, delete-orphan"
    )


# ─────────────────────────────────────────────────────────────────────────────
#  DocumentChunk – a text chunk with its embedding for RAG retrieval
# ─────────────────────────────────────────────────────────────────────────────
class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id", ondelete="CASCADE"), index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # pgvector column — dimension must match settings.embedding_dimensions
    embedding: Mapped[Optional[list]] = mapped_column(
        Vector(settings.embedding_dimensions), nullable=True
    )
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    source: Mapped["Source"] = relationship("Source", back_populates="chunks")


# ─────────────────────────────────────────────────────────────────────────────
#  Contradiction – conflicting claims found between two sources
# ─────────────────────────────────────────────────────────────────────────────
class Contradiction(Base):
    __tablename__ = "contradictions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    claim_a: Mapped[str] = mapped_column(Text, nullable=False)
    source_a_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id", ondelete="SET NULL"), nullable=True
    )
    claim_b: Mapped[str] = mapped_column(Text, nullable=False)
    source_b_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id", ondelete="SET NULL"), nullable=True
    )
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolution_tip: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    project: Mapped["Project"] = relationship("Project", back_populates="contradictions")


# ─────────────────────────────────────────────────────────────────────────────
#  ResearchGap – topics not covered in the collected literature
# ─────────────────────────────────────────────────────────────────────────────
class ResearchGap(Base):
    __tablename__ = "research_gaps"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    gap_title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    project: Mapped["Project"] = relationship("Project", back_populates="research_gaps")


# ─────────────────────────────────────────────────────────────────────────────
#  Report – the final generated research report
# ─────────────────────────────────────────────────────────────────────────────
class Report(Base):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    markdown_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    citations: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    pptx_file_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    project: Mapped["Project"] = relationship("Project", back_populates="report")
