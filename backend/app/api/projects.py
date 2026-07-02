"""
ResearchMind AI – Projects Router
Handles CRUD operations for research projects and kicks off the agent workflow.
"""
import logging
import uuid
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents import research_graph, ResearchState
from app.database import get_db
from app.models import Contradiction, Project, Report, ResearchGap, Source
from app.schemas import (
    ContradictionResponse,
    MessageResponse,
    ProjectCreate,
    ProjectDetailResponse,
    ProjectResponse,
    ResearchGapResponse,
    SourceResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/projects", tags=["Projects"])


# ─────────────────────────────────────────────────────────────────────────────
#  Background task – runs the LangGraph pipeline
# ─────────────────────────────────────────────────────────────────────────────
async def run_research_pipeline(project_id: str, topic: str) -> None:
    """
    Executed asynchronously so the POST /projects endpoint returns immediately.
    Invokes the full Planner→Researcher→Critic→Writer→Reviewer graph.
    """
    from app.database import AsyncSessionLocal

    logger.info("[Pipeline] Starting research for project %s", project_id)

    initial_state: ResearchState = {
        "project_id": project_id,
        "topic": topic,
        "objectives": [],
        "subtopics": [],
        "questions": [],
        "sources": [],
        "contradictions": [],
        "verified_sources": [],
        "draft_sections": {},
        "citations": {},
        "gaps": [],
        "review_passed": False,
        "confidence_score": None,
        "iteration_count": 0,
        "final_report": None,
        "messages": [],
    }

    try:
        # Update status → planning
        async with AsyncSessionLocal() as session:
            project = await session.get(Project, uuid.UUID(project_id))
            if project:
                project.status = "planning"
                await session.commit()

        # ── Run the graph ────────────────────────────────────────────────────
        final_state: ResearchState = await research_graph.ainvoke(initial_state)
        # ─────────────────────────────────────────────────────────────────────

        # Persist results to the database
        async with AsyncSessionLocal() as session:
            project = await session.get(Project, uuid.UUID(project_id))
            if not project:
                return

            project.subtopics = final_state.get("subtopics", [])
            project.research_questions = final_state.get("questions", [])
            project.status = "done"
            project.confidence_score = final_state.get("confidence_score", 0.75)

            # Persist sources
            for src_data in final_state.get("verified_sources", []):
                source = Source(
                    project_id=project.id,
                    title=src_data.get("title", "Unknown"),
                    url=src_data.get("url"),
                    source_type=src_data.get("source_type", "web"),
                    reliability_score=src_data.get("reliability"),
                )
                session.add(source)

            # Persist contradictions
            for con_data in final_state.get("contradictions", []):
                contradiction = Contradiction(
                    project_id=project.id,
                    claim_a=con_data.get("claim_a", ""),
                    claim_b=con_data.get("claim_b", ""),
                    explanation=con_data.get("explanation"),
                    resolution_tip=con_data.get("resolution_tip"),
                )
                session.add(contradiction)

            # Persist research gaps
            for gap_data in final_state.get("gaps", []):
                gap = ResearchGap(
                    project_id=project.id,
                    gap_title=gap_data.get("gap_title", ""),
                    description=gap_data.get("description"),
                    evidence=gap_data.get("evidence"),
                )
                session.add(gap)

            # Persist report
            report = Report(
                project_id=project.id,
                markdown_content=final_state.get("final_report"),
                citations=final_state.get("citations"),
            )
            session.add(report)

            # Generate PPTX presentation
            try:
                from app.services.pptx_generator import generate_pptx
                pptx_path = generate_pptx(
                    topic=topic,
                    objectives=final_state.get("objectives", []),
                    subtopics=final_state.get("subtopics", []),
                    draft_sections=final_state.get("draft_sections", {}),
                    gaps=final_state.get("gaps", []),
                    sources=final_state.get("verified_sources", []),
                    citations=final_state.get("citations", {}),
                    confidence_score=final_state.get("confidence_score"),
                )
                report.pptx_file_path = pptx_path
                logger.info("[Pipeline] PPTX generated: %s", pptx_path)
            except Exception as pptx_exc:
                logger.warning("[Pipeline] PPTX generation failed: %s", pptx_exc)

            await session.commit()
            logger.info("[Pipeline] Project %s completed successfully.", project_id)

    except Exception as exc:
        logger.exception("[Pipeline] Project %s failed: %s", project_id, exc)
        async with AsyncSessionLocal() as session:
            project = await session.get(Project, uuid.UUID(project_id))
            if project:
                project.status = "failed"
                await session.commit()


# ─────────────────────────────────────────────────────────────────────────────
#  Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=ProjectResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create a new research project and trigger the agent pipeline",
)
async def create_project(
    payload: ProjectCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """
    Creates a Project record and immediately returns 202 Accepted.
    The multi-agent research pipeline runs asynchronously in the background.
    Poll GET /projects/{id} to track progress.
    """
    project = Project(topic=payload.topic, status="pending")
    db.add(project)
    await db.flush()          # get the generated UUID without committing
    project_id = str(project.id)
    await db.commit()
    await db.refresh(project)

    # Kick off background pipeline
    background_tasks.add_task(run_research_pipeline, project_id, payload.topic)
    logger.info("[API] Project %s created. Pipeline queued.", project_id)

    return project


@router.get(
    "/",
    response_model=List[ProjectResponse],
    summary="List all research projects",
)
async def list_projects(
    db: AsyncSession = Depends(get_db),
) -> List[ProjectResponse]:
    result = await db.execute(
        select(Project).order_by(Project.created_at.desc())
    )
    return result.scalars().all()


@router.get(
    "/{project_id}",
    response_model=ProjectDetailResponse,
    summary="Get project details with counts",
)
async def get_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ProjectDetailResponse:
    result = await db.execute(
        select(Project)
        .where(Project.id == project_id)
        .options(
            selectinload(Project.sources),
            selectinload(Project.contradictions),
            selectinload(Project.research_gaps),
        )
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return ProjectDetailResponse(
        **ProjectResponse.model_validate(project).model_dump(),
        sources_count=len(project.sources),
        contradictions_count=len(project.contradictions),
        gaps_count=len(project.research_gaps),
    )


@router.delete(
    "/{project_id}",
    response_model=MessageResponse,
    summary="Delete a research project and all related data",
)
async def delete_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    await db.delete(project)
    await db.commit()
    return MessageResponse(message=f"Project {project_id} deleted successfully.")


# ─────────────────────────────────────────────────────────────────────────────
#  Sub-resource endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/{project_id}/sources",
    response_model=List[SourceResponse],
    summary="List all sources for a project with reliability scores",
)
async def list_sources(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> List[SourceResponse]:
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    result = await db.execute(
        select(Source).where(Source.project_id == project_id).order_by(Source.fetched_at.desc())
    )
    return result.scalars().all()


@router.get(
    "/{project_id}/contradictions",
    response_model=List[ContradictionResponse],
    summary="List all contradictions found in a project",
)
async def list_contradictions(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> List[ContradictionResponse]:
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    result = await db.execute(
        select(Contradiction).where(Contradiction.project_id == project_id)
    )
    return result.scalars().all()


@router.get(
    "/{project_id}/gaps",
    response_model=List[ResearchGapResponse],
    summary="List all research gaps identified in a project",
)
async def list_gaps(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> List[ResearchGapResponse]:
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    result = await db.execute(
        select(ResearchGap).where(ResearchGap.project_id == project_id)
    )
    return result.scalars().all()

