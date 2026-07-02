"""
ResearchMind AI – PDF Upload Endpoint
Accepts PDF files, extracts text, chunks it, generates embeddings,
and stores the content as DocumentChunks linked to a Source.
"""
import logging
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import DocumentChunk, Project, Source
from app.schemas import SourceResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/projects", tags=["Uploads"])


CHUNK_SIZE = 400
CHUNK_OVERLAP = 80


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks."""
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end].strip())
        start += chunk_size - overlap
    return [c for c in chunks if len(c) > 30]


@router.post(
    "/{project_id}/upload-pdf",
    response_model=SourceResponse,
    summary="Upload a PDF research paper to a project",
)
async def upload_pdf(
    project_id: uuid.UUID,
    file: UploadFile = File(..., description="PDF file to upload"),
    db: AsyncSession = Depends(get_db),
) -> SourceResponse:
    """
    Upload a PDF file. The server will:
    1. Verify the project exists
    2. Extract text from all pages using pdfplumber
    3. Chunk the text with overlap
    4. Generate embeddings for each chunk (sentence-transformers)
    5. Store a Source record + DocumentChunk records
    """
    # Validate project
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    # Read PDF bytes
    content = await file.read()
    if len(content) > 50 * 1024 * 1024:  # 50 MB limit
        raise HTTPException(status_code=400, detail="File too large (max 50 MB)")

    # Extract text
    try:
        import pdfplumber
        import io

        all_text = ""
        page_texts: list[tuple[int, str]] = []

        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text() or ""
                all_text += text + "\n"
                page_texts.append((page_num, text))

    except Exception as exc:
        logger.exception("[Upload] PDF extraction failed: %s", exc)
        raise HTTPException(status_code=400, detail=f"Could not read PDF: {exc}")

    if not all_text.strip():
        raise HTTPException(status_code=400, detail="No text could be extracted from this PDF")

    # Create Source record
    source = Source(
        project_id=project_id,
        title=file.filename or "Uploaded PDF",
        url=None,
        source_type="pdf",
        reliability_score=0.85,  # PDFs uploaded by user get reasonable default
        justification="User-uploaded research paper",
    )
    db.add(source)
    await db.flush()  # get source.id

    # Chunk and embed
    try:
        from app.agents.llm import get_embeddings
        embeddings_model = get_embeddings()

        chunk_index = 0
        for page_num, page_text in page_texts:
            chunks = chunk_text(page_text)
            if not chunks:
                continue

            chunk_embeddings = embeddings_model.embed_documents(chunks)

            for text_chunk, embedding in zip(chunks, chunk_embeddings):
                doc_chunk = DocumentChunk(
                    source_id=source.id,
                    content=text_chunk,
                    embedding=embedding,
                    page_number=page_num,
                    chunk_index=chunk_index,
                )
                db.add(doc_chunk)
                chunk_index += 1

        logger.info(
            "[Upload] PDF '%s' → %d chunks stored for project %s",
            file.filename, chunk_index, project_id,
        )

    except Exception as exc:
        logger.exception("[Upload] Embedding generation failed: %s", exc)
        # Still save source without embeddings
        pass

    await db.commit()
    await db.refresh(source)
    return source
