"""
ResearchMind AI – Researcher Agent
Searches the web via Tavily for each research question, stores chunked
content with embeddings in the document_chunks table, and returns a list
of sources.
"""
import logging
import uuid
from typing import Any, Dict, List

from tavily import TavilyClient

from app.agents.llm import get_embeddings
from app.config import get_settings

logger = logging.getLogger(__name__)

CHUNK_SIZE = 400       # characters per chunk (approximate)
CHUNK_OVERLAP = 80     # overlap between consecutive chunks


# ── Text chunking ─────────────────────────────────────────────────────────────
def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Split text into overlapping chunks."""
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end].strip())
        start += chunk_size - overlap
    return [c for c in chunks if len(c) > 30]   # drop tiny fragments


# ── Agent Node Function ───────────────────────────────────────────────────────
async def researcher_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Researcher Agent Node
    Input:  state["questions"], state["project_id"]
    Output: sources list
    """
    import asyncio
    questions: List[str] = state.get("questions", [])
    project_id: str = state.get("project_id", "")

    logger.info("[Researcher] Searching for %d questions", len(questions))

    from app.api.ws import emit_agent_event
    if project_id:
        await emit_agent_event(
            project_id,
            "researcher",
            "started",
            f"Kicking off search for {len(questions)} research questions."
        )

    settings = get_settings()
    tavily = TavilyClient(api_key=settings.tavily_api_key)

    sources: List[Dict[str, Any]] = []
    seen_urls: set = set()

    for idx, question in enumerate(questions, 1):
        logger.info("[Researcher] Searching: %s", question)
        if project_id:
            await emit_agent_event(
                project_id,
                "researcher",
                "started",
                f"Searching [{idx}/{len(questions)}]: '{question}'"
            )
        try:
            # Run blocking Tavily search in a thread pool
            response = await asyncio.to_thread(
                tavily.search,
                query=question,
                max_results=settings.max_search_results_per_query,
                include_raw_content=True,
                search_depth="advanced",
            )
            results = response.get("results", [])

            for item in results:
                url = item.get("url", "")
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                raw_content = item.get("raw_content") or item.get("content", "")
                title = item.get("title", "Unknown")

                # Generate chunks and embeddings
                chunks = chunk_text(raw_content)
                embeddings_model = get_embeddings()
                chunk_embeddings: List[List[float]] = []
                if chunks:
                    chunk_embeddings = await asyncio.to_thread(
                        embeddings_model.embed_documents, chunks
                    )

                sources.append({
                    "title": title[:512],
                    "url": url,
                    "source_type": "web",
                    "content": raw_content[:5000],   # cap for in-memory state
                    "reliability": None,             # scored by Critic agent
                    "chunks": chunks,
                    "embeddings": chunk_embeddings,
                })

        except Exception as exc:
            logger.warning("[Researcher] Search failed for question '%s': %s", question, exc)
            continue

    logger.info("[Researcher] Collected %d unique sources", len(sources))
    if project_id:
        await emit_agent_event(
            project_id,
            "researcher",
            "completed",
            f"Search complete. Gathered {len(sources)} sources.",
            {"sources_count": len(sources)}
        )
    return {"sources": sources}
