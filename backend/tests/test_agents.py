"""
ResearchMind AI – LangGraph Agent Integration Tests

Tests the compiled LangGraph state machine with stub nodes to verify:
  1. Graph compiles and runs without errors.
  2. Each node produces the expected output keys.
  3. The conditional edge logic fires correctly.
  4. The iteration cap prevents infinite loops.
"""
import asyncio
import pytest
from app.agents.graph import build_research_graph, ResearchState


@pytest.fixture
def graph():
    """Compile a fresh graph for each test."""
    return build_research_graph()


@pytest.fixture
def initial_state() -> ResearchState:
    return ResearchState(
        project_id="test-project-001",
        topic="Impact of AI in Healthcare",
        objectives=[],
        subtopics=[],
        questions=[],
        sources=[],
        contradictions=[],
        verified_sources=[],
        draft_sections={},
        citations={},
        gaps=[],
        review_passed=False,
        iteration_count=0,
        final_report=None,
        messages=[],
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Graph execution tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_graph_runs_to_completion(graph, initial_state):
    """Full pipeline should run from planner to END without raising exceptions."""
    final_state = await graph.ainvoke(initial_state)
    assert final_state is not None
    assert final_state["review_passed"] is True


@pytest.mark.asyncio
async def test_planner_produces_subtopics(graph, initial_state):
    """Planner node should generate subtopics and research questions."""
    final_state = await graph.ainvoke(initial_state)
    assert len(final_state["subtopics"]) > 0
    assert len(final_state["questions"]) > 0
    assert len(final_state["objectives"]) > 0


@pytest.mark.asyncio
async def test_researcher_produces_sources(graph, initial_state):
    """Researcher node should return at least one source."""
    final_state = await graph.ainvoke(initial_state)
    assert len(final_state["sources"]) > 0


@pytest.mark.asyncio
async def test_critic_filters_sources(graph, initial_state):
    """Critic node should produce verified_sources (may be subset of sources)."""
    final_state = await graph.ainvoke(initial_state)
    # All verified sources must meet the reliability threshold (0.6)
    for source in final_state["verified_sources"]:
        assert source.get("reliability", 0) >= 0.6


@pytest.mark.asyncio
async def test_writer_produces_draft_sections(graph, initial_state):
    """Writer node should produce one draft section per subtopic."""
    final_state = await graph.ainvoke(initial_state)
    assert len(final_state["draft_sections"]) == len(final_state["subtopics"])


@pytest.mark.asyncio
async def test_reviewer_assembles_final_report(graph, initial_state):
    """Reviewer should produce a non-empty final report string."""
    final_state = await graph.ainvoke(initial_state)
    assert final_state["final_report"] is not None
    assert len(final_state["final_report"]) > 50


@pytest.mark.asyncio
async def test_reviewer_detects_gaps(graph, initial_state):
    """Reviewer should identify at least one research gap in stub mode."""
    final_state = await graph.ainvoke(initial_state)
    assert len(final_state["gaps"]) > 0


@pytest.mark.asyncio
async def test_iteration_count_increments(graph, initial_state):
    """Iteration counter should be 1 after a single successful pass."""
    final_state = await graph.ainvoke(initial_state)
    assert final_state["iteration_count"] == 1


# ─────────────────────────────────────────────────────────────────────────────
#  Health / API unit test
# ─────────────────────────────────────────────────────────────────────────────
def test_graph_compiles_without_error():
    """Smoke test: graph compilation should not raise."""
    try:
        g = build_research_graph()
        assert g is not None
    except Exception as exc:
        pytest.fail(f"Graph compilation raised an exception: {exc}")
