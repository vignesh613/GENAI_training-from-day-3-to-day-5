from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from agents.researcher import researcher_node
from agents.writer import writer_node
from agents.editor import editor_node, should_revise
from utils.logger import get_logger

logger = get_logger(__name__)


class AgentState(TypedDict):
    topic: str
    research_notes: str
    retrieved_context: str
    draft_report: str
    final_report: str
    quality_score: int
    revision_count: int
    status: str
    report_id: str
    errors: List[str]


def increment_revision(state: AgentState) -> AgentState:
    new_count = state.get("revision_count", 0) + 1
    logger.info(f"[GRAPH] Revision count → {new_count}")
    return {**state, "revision_count": new_count}


def build_workflow():
    graph = StateGraph(AgentState)

    graph.add_node("researcher", researcher_node)
    graph.add_node("writer", writer_node)
    graph.add_node("editor", editor_node)
    graph.add_node("increment_revision", increment_revision)

    graph.set_entry_point("researcher")
    graph.add_edge("researcher", "writer")
    graph.add_edge("writer", "editor")

    # Feedback loop: editor → increment_revision → writer (if quality low)
    graph.add_conditional_edges(
        "editor",
        should_revise,
        {
            "revise": "increment_revision",
            "complete": END,
        },
    )
    graph.add_edge("increment_revision", "writer")

    compiled = graph.compile()
    logger.info("[GRAPH] Workflow compiled: Researcher → Writer → Editor (↺ feedback loop)")
    return compiled


_workflow = None


def get_workflow():
    global _workflow
    if _workflow is None:
        _workflow = build_workflow()
    return _workflow


async def run_report_workflow(topic: str, report_id: str) -> dict:
    logger.info(f"[GRAPH] Starting workflow — report {report_id[:8]}...")

    initial_state: AgentState = {
        "topic": topic,
        "research_notes": "",
        "retrieved_context": "",
        "draft_report": "",
        "final_report": "",
        "quality_score": 0,
        "revision_count": 0,
        "status": "starting",
        "report_id": report_id,
        "errors": [],
    }

    workflow = get_workflow()
    result = await workflow.ainvoke(initial_state)

    logger.info(
        f"[GRAPH] Workflow complete — {report_id[:8]} | "
        f"score={result.get('quality_score')}/10 | revisions={result.get('revision_count')}"
    )
    return result
