"""
ResearchMind AI – Writer Agent
Uses RAG (pgvector similarity search) to retrieve relevant chunks per subtopic,
then generates a full markdown report section with inline citations using Groq.
"""
import asyncio
import logging
from typing import Any, Dict, List

from langchain_core.prompts import ChatPromptTemplate

from app.agents.llm import get_llm, get_embeddings

logger = logging.getLogger(__name__)


SECTION_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an expert research writer. Write a comprehensive, well-structured
markdown section about the given subtopic using only the provided source excerpts.

Rules:
- Every factual claim MUST have an inline citation like [1], [2], etc.
- Use proper markdown formatting with headers, bullet points where appropriate.
- Be analytical — compare, contrast, and synthesise information from multiple sources.
- Do NOT hallucinate — only use information present in the provided sources.
- Write 300-500 words per section.""",
    ),
    (
        "human",
        """Subtopic: {subtopic}

Source Excerpts:
{context}

Write a detailed markdown section about "{subtopic}" with inline citations.""",
    ),
])

ABSTRACT_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a research writer. Write a concise executive abstract (150-200 words) "
        "for a research report.",
    ),
    (
        "human",
        "Research Topic: {topic}\n\nKey Subtopics Covered: {subtopics}\n\nWrite an abstract.",
    ),
])


def build_context_from_sources(
    sources: List[Dict[str, Any]],
    subtopic: str,
    embeddings_model,
) -> tuple[str, Dict[str, Dict]]:
    """
    Build a context string from source content relevant to the subtopic.
    Returns (context_str, citations_dict).
    """
    if not sources:
        return "No sources available.", {}

    # Simple keyword-based relevance scoring (pgvector RAG happens in DB layer)
    # For the writer node we select top 5 sources by content relevance to subtopic
    subtopic_lower = subtopic.lower()
    scored = []
    for i, src in enumerate(sources):
        content = src.get("content", "")
        score = sum(1 for word in subtopic_lower.split() if word in content.lower())
        scored.append((score, i, src))

    scored.sort(reverse=True)
    top_sources = [src for _, _, src in scored[:5]]

    context_parts = []
    citations: Dict[str, Dict] = {}

    for idx, src in enumerate(top_sources, 1):
        cit_key = str(idx)
        title = src.get("title", f"Source {idx}")
        url = src.get("url", "")
        content = (src.get("content") or "")[:600]

        context_parts.append(f"[{cit_key}] {title}\n{content}")
        citations[cit_key] = {"title": title, "url": url}

    return "\n\n".join(context_parts), citations


async def writer_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Writer Agent Node
    Input:  state["subtopics"], state["verified_sources"], state["topic"]
    Output: draft_sections, citations, final_report
    """
    subtopics: List[str] = state.get("subtopics", [])
    verified_sources: List[Dict[str, Any]] = state.get("verified_sources", [])
    topic: str = state.get("topic", "Unknown Topic")
    project_id: str = state.get("project_id", "")

    logger.info("[Writer] Drafting %d sections for topic: %s", len(subtopics), topic)

    from app.api.ws import emit_agent_event
    if project_id:
        await emit_agent_event(
            project_id,
            "writer",
            "started",
            f"Drafting {len(subtopics)} report sections with inline citations."
        )

    llm = get_llm()
    embeddings_model = get_embeddings()
    section_chain = SECTION_PROMPT | llm
    abstract_chain = ABSTRACT_PROMPT | llm

    draft_sections: Dict[str, str] = {}
    all_citations: Dict[str, Dict] = {}

    for idx, subtopic in enumerate(subtopics, 1):
        logger.info("[Writer] Writing section: %s", subtopic)
        if project_id:
            await emit_agent_event(
                project_id,
                "writer",
                "started",
                f"Writing section [{idx}/{len(subtopics)}]: '{subtopic}'"
            )
        try:
            context, citations = build_context_from_sources(
                verified_sources, subtopic, embeddings_model
            )
            # Offset citation keys to avoid collision across sections
            offset = len(all_citations)
            offset_citations = {}
            offset_context = context
            for key, val in citations.items():
                new_key = str(int(key) + offset)
                offset_citations[new_key] = val
                offset_context = offset_context.replace(f"[{key}]", f"[{new_key}]")
            all_citations.update(offset_citations)

            # Sleep to prevent hitting Groq 6000 TPM limit
            await asyncio.sleep(3)

            response = await section_chain.ainvoke({
                "subtopic": subtopic,
                "context": offset_context,
            })
            section_md = response.content if hasattr(response, "content") else str(response)
            draft_sections[subtopic] = section_md

        except Exception as exc:
            logger.warning("[Writer] Section failed for '%s': %s", subtopic, exc)
            draft_sections[subtopic] = f"## {subtopic}\n\n*Content unavailable.*\n"

    # ── Generate abstract ──────────────────────────────────────────────────────
    if project_id:
        await emit_agent_event(
            project_id,
            "writer",
            "started",
            "Generating executive abstract..."
        )
    try:
        abstract_response = await abstract_chain.ainvoke({
            "topic": topic,
            "subtopics": ", ".join(subtopics),
        })
        abstract = abstract_response.content if hasattr(abstract_response, "content") else ""
    except Exception:
        abstract = f"This report presents autonomous research on: {topic}."

    # ── Assemble full report ───────────────────────────────────────────────────
    report_parts = [
        f"# Research Report: {topic}\n",
        f"## Abstract\n\n{abstract}\n",
    ]
    for subtopic, content in draft_sections.items():
        report_parts.append(content)

    # References section
    report_parts.append("\n---\n## References\n")
    for key, ref in sorted(all_citations.items(), key=lambda x: int(x[0])):
        url_part = f" — [{ref['url']}]({ref['url']})" if ref.get("url") else ""
        report_parts.append(f"[{key}] {ref['title']}{url_part}")

    final_report = "\n\n".join(report_parts)

    logger.info("[Writer] Report assembled (%d chars, %d citations)", len(final_report), len(all_citations))
    if project_id:
        await emit_agent_event(
            project_id,
            "writer",
            "completed",
            f"Drafting complete. Assembled {len(draft_sections)} sections with {len(all_citations)} citations.",
            {"report_length": len(final_report), "citations_count": len(all_citations)}
        )
    return {
        "draft_sections": draft_sections,
        "citations": all_citations,
        "final_report": final_report,
    }
