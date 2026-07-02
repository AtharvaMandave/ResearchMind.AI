"""
ResearchMind AI – Planner Agent
Breaks a research topic into objectives, subtopics, and research questions
using Groq Llama3 70B with structured output.
"""
import logging
from typing import Any, Dict, List

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.agents.llm import get_llm

logger = logging.getLogger(__name__)


# ── Structured Output Schema ──────────────────────────────────────────────────
class PlannerOutput(BaseModel):
    objectives: List[str] = Field(description="3-5 high-level research objectives")
    subtopics: List[str] = Field(description="4-7 focused subtopics to research")
    questions: List[str] = Field(description="8-15 specific research questions, 2-3 per subtopic")


# ── Prompt ────────────────────────────────────────────────────────────────────
PLANNER_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an expert research planner. Given a research topic, your job is to:
1. Define clear research objectives
2. Break the topic into focused subtopics
3. Generate specific, answerable research questions for each subtopic

Be thorough but focused. Each question should be searchable on the web.""",
    ),
    (
        "human",
        "Research Topic: {topic}\n\nGenerate a complete research plan.",
    ),
])


# ── Agent Node Function ───────────────────────────────────────────────────────
async def planner_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Planner Agent Node
    Input:  state["topic"]
    Output: objectives, subtopics, questions
    """
    topic = state["topic"]
    project_id = state.get("project_id", "")
    logger.info("[Planner] Planning research for topic: %s", topic)

    from app.api.ws import emit_agent_event
    if project_id:
        await emit_agent_event(project_id, "planner", "started", f"Structuring research objectives for: '{topic}'")

    try:
        llm = get_llm()
        structured_llm = llm.with_structured_output(PlannerOutput)
        chain = PLANNER_PROMPT | structured_llm

        result: PlannerOutput = await chain.ainvoke({"topic": topic})

        logger.info(
            "[Planner] Generated %d subtopics, %d questions",
            len(result.subtopics),
            len(result.questions),
        )

        if project_id:
            await emit_agent_event(
                project_id,
                "planner",
                "completed",
                f"Generated {len(result.subtopics)} subtopics and {len(result.questions)} research questions.",
                {"subtopics": result.subtopics, "objectives": result.objectives}
            )

        return {
            "objectives": result.objectives,
            "subtopics": result.subtopics,
            "questions": result.questions,
        }

    except Exception as exc:
        logger.exception("[Planner] Failed: %s", exc)
        fallback = {
            "objectives": [f"Research the topic: {topic}"],
            "subtopics": [f"{topic} – Overview", f"{topic} – Applications", f"{topic} – Challenges"],
            "questions": [
                f"What is {topic}?",
                f"What are the main applications of {topic}?",
                f"What are the challenges in {topic}?",
            ],
        }
        if project_id:
            await emit_agent_event(
                project_id,
                "planner",
                "completed",
                "Planning completed with fallback objectives.",
                {"subtopics": fallback["subtopics"], "objectives": fallback["objectives"]}
            )
        return fallback
