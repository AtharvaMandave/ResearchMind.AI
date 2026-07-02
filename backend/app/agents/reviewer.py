"""
ResearchMind AI – Reviewer Agent
Checks report quality, identifies research gaps, computes confidence score,
and decides whether to loop back to the Planner or finalize.
"""
import logging
from typing import Any, Dict, List

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.agents.llm import get_llm

logger = logging.getLogger(__name__)


# ── Structured output schemas ─────────────────────────────────────────────────
class ResearchGap(BaseModel):
    gap_title: str = Field(description="Short title for the research gap")
    description: str = Field(description="What is missing from the research")
    evidence: str = Field(description="Why this gap exists — what was not found")


class ReviewOutput(BaseModel):
    review_passed: bool = Field(
        description="True if the report is complete and high-quality"
    )
    gaps: List[ResearchGap] = Field(
        description="List of research gaps — topics not adequately covered"
    )
    confidence_score: float = Field(
        ge=0.0, le=1.0,
        description="Confidence score from 0 to 1 based on source quality and coverage",
    )
    feedback: str = Field(description="Brief feedback on what is missing or needs improvement")


REVIEWER_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are a senior research reviewer. Your job is to critically evaluate a research report.

Assess:
1. Completeness — are all subtopics adequately covered?
2. Citation coverage — are claims backed by sources?
3. Research gaps — what important angles are missing?
4. Overall quality

Assign a confidence score:
- 0.9+ = Excellent: well-cited, comprehensive, no major gaps
- 0.7-0.9 = Good: mostly complete with minor gaps
- 0.5-0.7 = Fair: significant gaps or weak citations
- Below 0.5 = Poor: needs major revision""",
    ),
    (
        "human",
        """Research Topic: {topic}

Subtopics Covered: {subtopics}

Number of Sources: {source_count}
Number of Citations: {citation_count}

Report Preview (first 2000 chars):
{report_preview}

Evaluate this report thoroughly.""",
    ),
])


# ── Confidence scoring helpers ────────────────────────────────────────────────
def compute_base_confidence(
    source_count: int,
    citation_count: int,
    verified_sources: List[Dict[str, Any]],
) -> float:
    """Compute a base confidence from quantitative metrics."""
    if source_count == 0:
        return 0.1

    # Average reliability of verified sources
    reliability_scores = [
        s.get("reliability", 0.5) for s in verified_sources if s.get("reliability") is not None
    ]
    avg_reliability = sum(reliability_scores) / len(reliability_scores) if reliability_scores else 0.5

    # Source count factor (caps at 10 sources → 1.0)
    source_factor = min(source_count / 10, 1.0)

    # Citation factor
    citation_factor = min(citation_count / 15, 1.0)

    return round((avg_reliability * 0.5 + source_factor * 0.3 + citation_factor * 0.2), 2)


# ── Agent Node Function ───────────────────────────────────────────────────────
async def reviewer_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Reviewer Agent Node
    Input:  state["final_report"], state["subtopics"], state["verified_sources"],
            state["citations"], state["iteration_count"]
    Output: gaps, review_passed, confidence_score, iteration_count
    """
    topic = state.get("topic", "Unknown")
    subtopics = state.get("subtopics", [])
    verified_sources = state.get("verified_sources", [])
    citations = state.get("citations", {})
    final_report = state.get("final_report", "")
    iteration_count = state.get("iteration_count", 0)
    project_id = state.get("project_id", "")

    source_count = len(verified_sources)
    citation_count = len(citations)

    logger.info(
        "[Reviewer] Reviewing report. Sources: %d, Citations: %d, Iteration: %d",
        source_count, citation_count, iteration_count,
    )

    from app.api.ws import emit_agent_event
    if project_id:
        await emit_agent_event(
            project_id,
            "reviewer",
            "started",
            f"Reviewing final report draft (iteration {iteration_count}). Evaluating quality and gaps."
        )

    base_confidence = compute_base_confidence(source_count, citation_count, verified_sources)

    try:
        llm = get_llm()
        structured_llm = llm.with_structured_output(ReviewOutput)
        chain = REVIEWER_PROMPT | structured_llm

        result: ReviewOutput = await chain.ainvoke({
            "topic": topic,
            "subtopics": ", ".join(subtopics),
            "source_count": source_count,
            "citation_count": citation_count,
            "report_preview": final_report[:2000],
        })

        # Blend LLM confidence with quantitative base score
        blended_confidence = round((result.confidence_score * 0.6 + base_confidence * 0.4), 2)
        gaps = [g.model_dump() for g in result.gaps]

        logger.info(
            "[Reviewer] review_passed=%s, confidence=%.2f, gaps=%d",
            result.review_passed, blended_confidence, len(gaps),
        )

        if project_id:
            await emit_agent_event(
                project_id,
                "reviewer",
                "completed",
                f"Review complete. Status: {'Passed' if result.review_passed else 'Needs revision'}. Confidence score: {blended_confidence}",
                {
                    "review_passed": result.review_passed,
                    "confidence_score": blended_confidence,
                    "gaps_count": len(gaps)
                }
            )

        return {
            "gaps": gaps,
            "review_passed": result.review_passed,
            "confidence_score": blended_confidence,
            "iteration_count": iteration_count + 1,
        }

    except Exception as exc:
        logger.exception("[Reviewer] LLM review failed: %s", exc)
        if project_id:
            await emit_agent_event(
                project_id,
                "reviewer",
                "completed",
                f"Review complete (fallback bypass). Confidence score: {base_confidence}",
                {
                    "review_passed": True,
                    "confidence_score": base_confidence,
                    "gaps_count": 0
                }
            )
        # Fallback: pass with computed confidence
        return {
            "gaps": [],
            "review_passed": True,
            "confidence_score": base_confidence,
            "iteration_count": iteration_count + 1,
        }
