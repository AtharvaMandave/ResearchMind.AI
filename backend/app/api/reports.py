"""
ResearchMind AI – Reports Router
Endpoints for fetching reports and downloading exports.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
import os
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Report
from app.schemas import ReportResponse

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get(
    "/{project_id}",
    response_model=ReportResponse,
    summary="Fetch the generated research report for a project",
)
async def get_report(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ReportResponse:
    result = await db.execute(
        select(Report).where(Report.project_id == project_id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(
            status_code=404,
            detail="Report not found. The research pipeline may still be running.",
        )
    return report


@router.get(
    "/{project_id}/markdown",
    response_class=PlainTextResponse,
    summary="Download the raw Markdown report",
)
async def download_markdown(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> str:
    result = await db.execute(
        select(Report).where(Report.project_id == project_id)
    )
    report = result.scalar_one_or_none()
    if not report or not report.markdown_content:
        raise HTTPException(status_code=404, detail="Report not available yet.")
    return report.markdown_content


@router.get(
    "/{project_id}/pptx",
    response_class=FileResponse,
    summary="Download the generated PowerPoint presentation",
)
async def download_pptx(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    result = await db.execute(
        select(Report).where(Report.project_id == project_id)
    )
    report = result.scalar_one_or_none()
    if not report or not report.pptx_file_path:
        raise HTTPException(
            status_code=404,
            detail="PPTX presentation not available for this project.",
        )
    if not os.path.exists(report.pptx_file_path):
        raise HTTPException(
            status_code=404,
            detail="PPTX file not found on disk. It may have been cleaned up.",
        )
    return FileResponse(
        path=report.pptx_file_path,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=f"Research_Report_{project_id}.pptx",
    )
