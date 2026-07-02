"""
ResearchMind AI – LangGraph Multi-Agent State & Graph Definition

Nodes:
    planner    → Breaks topic into subtopics + questions (Groq Llama3 70B)
    researcher → Searches Tavily, generates embeddings (sentence-transformers)
    critic     → Scores reliability, detects contradictions (Groq Llama3 70B)
    writer     → RAG-based markdown report generation (Groq Llama3 70B)
    reviewer   → Quality check, gap detection, confidence score (Groq Llama3 70B)

Flow:
    planner → researcher → critic → writer → reviewer
                ↑__________________________|  (conditional loop if review fails)
"""
from __future__ import annotations

import logging
from typing import Annotated, Any, Dict, List, Optional, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from app.agents.planner import planner_node
from app.agents.researcher import researcher_node
from app.agents.critic import critic_node
from app.agents.writer import writer_node
from app.agents.reviewer import reviewer_node

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
#  Shared State Definition
# ─────────────────────────────────────────────────────────────────────────────
class ResearchState(TypedDict):
    """
    The single source of truth passed between all LangGraph agent nodes.
    Each node reads what it needs, updates its outputs, and returns a partial dict.
    """
    project_id: str
    topic: str

    # Planner outputs
    objectives: List[str]
    subtopics: List[str]
    questions: List[str]

    # Researcher outputs
    sources: List[Dict[str, Any]]           # raw sources with content + embeddings

    # Critic outputs
    contradictions: List[Dict[str, Any]]    # {claim_a, claim_b, explanation, resolution_tip}
    verified_sources: List[Dict[str, Any]]  # sources passing reliability threshold

    # Writer outputs
    draft_sections: Dict[str, str]          # subtopic → markdown section
    citations: Dict[str, Dict[str, Any]]    # citation_key → {title, url}
    final_report: Optional[str]             # assembled full markdown report

    # Reviewer outputs
    gaps: List[Dict[str, Any]]              # {gap_title, description, evidence}
    review_passed: bool
    confidence_score: Optional[float]       # 0.0 – 1.0

    # Control
    iteration_count: int

    # LangChain message history
    messages: Annotated[List[BaseMessage], add_messages]


# ─────────────────────────────────────────────────────────────────────────────
#  Conditional Edge – loop back or finish?
# ─────────────────────────────────────────────────────────────────────────────
def should_continue(state: ResearchState) -> str:
    """
    After Reviewer runs, decide next step:
    - If review failed AND iterations < max → loop back to Planner
    - Otherwise → END
    """
    from app.config import get_settings
    settings = get_settings()

    review_passed = state.get("review_passed", False)
    iteration_count = state.get("iteration_count", 0)
    max_iterations = settings.max_agent_iterations

    if not review_passed and iteration_count < max_iterations:
        logger.info(
            "[Router] Review failed — looping back to Planner (iteration %d/%d)",
            iteration_count, max_iterations,
        )
        return "planner"
    else:
        logger.info("[Router] Research complete after %d iteration(s).", iteration_count)
        return END


# ─────────────────────────────────────────────────────────────────────────────
#  Graph Construction
# ─────────────────────────────────────────────────────────────────────────────
def build_research_graph() -> StateGraph:
    """
    Assembles and compiles the LangGraph state machine.

    planner → researcher → critic → writer → reviewer
                ↑___________________________|  (conditional loop)
    """
    graph = StateGraph(ResearchState)

    # Register agent nodes
    graph.add_node("planner", planner_node)
    graph.add_node("researcher", researcher_node)
    graph.add_node("critic", critic_node)
    graph.add_node("writer", writer_node)
    graph.add_node("reviewer", reviewer_node)

    # Linear path
    graph.set_entry_point("planner")
    graph.add_edge("planner", "researcher")
    graph.add_edge("researcher", "critic")
    graph.add_edge("critic", "writer")
    graph.add_edge("writer", "reviewer")

    # Conditional loop at Reviewer
    graph.add_conditional_edges(
        "reviewer",
        should_continue,
        {"planner": "planner", END: END},
    )

    return graph.compile()


# Singleton — import this in route handlers
research_graph = build_research_graph()
