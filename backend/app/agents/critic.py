"""
ResearchMind AI – Critic Agent
Scores source reliability and detects contradictions between sources.
"""
import logging
from typing import Any, Dict, List
from urllib.parse import urlparse

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.agents.llm import get_llm

logger = logging.getLogger(__name__)

# Domains that get a reliability bonus
HIGH_TRUST_DOMAINS = {
    "gov", "edu", "who.int", "cdc.gov", "nih.gov", "nature.com",
    "science.org", "pubmed.ncbi.nlm.nih.gov", "arxiv.org",
    "ncbi.nlm.nih.gov", "sciencedirect.com", "springer.com",
    "ieee.org", "acm.org", "researchgate.net",
}
LOW_TRUST_KEYWORDS = ["blog", "forum", "reddit", "quora", "yahoo", "buzzfeed"]

RELIABILITY_THRESHOLD = 0.45


def score_source_reliability(url: str) -> float:
    """Heuristic reliability score based on domain."""
    try:
        domain = urlparse(url).netloc.lower().lstrip("www.")
    except Exception:
        return 0.5

    for ht in HIGH_TRUST_DOMAINS:
        if ht in domain:
            return 0.90

    tld = domain.split(".")[-1] if "." in domain else ""
    if tld in ("gov", "edu"):
        return 0.90

    for lt in LOW_TRUST_KEYWORDS:
        if lt in domain:
            return 0.40

    return 0.65   # default for unknown domains


# ── Contradiction detection schema ────────────────────────────────────────────
class ContradictionCheck(BaseModel):
    has_contradiction: bool = Field(description="True if the two sources contradict each other")
    explanation: str = Field(description="Brief explanation of the contradiction or why there is none")
    resolution_tip: str = Field(description="Possible reason for the discrepancy, or 'N/A'")


CONTRADICTION_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a critical fact-checker. Compare two source summaries and determine "
        "if they present contradictory information on the same topic.",
    ),
    (
        "human",
        "Source A ({title_a}):\n{content_a}\n\n"
        "Source B ({title_b}):\n{content_b}\n\n"
        "Do these sources contradict each other on any factual claim?",
    ),
])


# ── Agent Node Function ───────────────────────────────────────────────────────
async def critic_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Critic Agent Node
    Input:  state["sources"]
    Output: verified_sources (scored + filtered), contradictions
    """
    sources: List[Dict[str, Any]] = state.get("sources", [])
    project_id: str = state.get("project_id", "")
    logger.info("[Critic] Validating %d sources", len(sources))

    from app.api.ws import emit_agent_event
    if project_id:
        await emit_agent_event(
            project_id,
            "critic",
            "started",
            f"Critiquing {len(sources)} sources and checking for factual contradictions."
        )

    # ── Step 1: Score reliability ─────────────────────────────────────────────
    for src in sources:
        src["reliability"] = score_source_reliability(src.get("url", ""))

    verified_sources = [s for s in sources if s["reliability"] >= RELIABILITY_THRESHOLD]
    logger.info(
        "[Critic] %d/%d sources passed reliability threshold (%.0f%%)",
        len(verified_sources), len(sources), RELIABILITY_THRESHOLD * 100,
    )

    # ── Step 2: Contradiction detection (compare top N sources pairwise) ──────
    contradictions: List[Dict[str, Any]] = []
    try:
        llm = get_llm()
        structured_llm = llm.with_structured_output(ContradictionCheck)
        chain = CONTRADICTION_PROMPT | structured_llm

        top_sources = verified_sources[:5]   # limit pairs to avoid excessive API calls
        pairs_checked = 0

        for i in range(len(top_sources)):
            for j in range(i + 1, len(top_sources)):
                if pairs_checked >= 6:    # cap at 6 pairs
                    break

                src_a = top_sources[i]
                src_b = top_sources[j]
                content_a = (src_a.get("content") or "")[:800]
                content_b = (src_b.get("content") or "")[:800]

                if not content_a or not content_b:
                    continue

                if project_id:
                    await emit_agent_event(
                        project_id,
                        "critic",
                        "started",
                        f"Comparing: '{src_a.get('title')[:30]}' vs '{src_b.get('title')[:30]}'"
                    )

                try:
                    result: ContradictionCheck = await chain.ainvoke({
                        "title_a": src_a.get("title", "Source A"),
                        "content_a": content_a,
                        "title_b": src_b.get("title", "Source B"),
                        "content_b": content_b,
                    })
                    if result.has_contradiction:
                        logger.info("[Critic] Contradiction found: %s", result.explanation)
                        contradictions.append({
                            "claim_a": f"{src_a['title']}: {content_a[:200]}",
                            "source_a_url": src_a.get("url"),
                            "claim_b": f"{src_b['title']}: {content_b[:200]}",
                            "source_b_url": src_b.get("url"),
                            "explanation": result.explanation,
                            "resolution_tip": result.resolution_tip,
                        })
                    pairs_checked += 1
                except Exception as exc:
                    logger.warning("[Critic] Contradiction check failed for pair: %s", exc)

    except Exception as exc:
        logger.exception("[Critic] Contradiction detection failed: %s", exc)

    logger.info("[Critic] Found %d contradictions", len(contradictions))
    if project_id:
        await emit_agent_event(
            project_id,
            "critic",
            "completed",
            f"Critique complete. Passed {len(verified_sources)} reliable sources. Detected {len(contradictions)} contradictions.",
            {"contradictions_count": len(contradictions), "verified_sources_count": len(verified_sources)}
        )
    return {
        "verified_sources": verified_sources,
        "contradictions": contradictions,
    }
