import logging
from typing import TypedDict
from langgraph.graph import StateGraph, END
from app.sentiment import analyze_sentiment

logger = logging.getLogger(__name__)

class WorkflowState(TypedDict):
    query: str
    sentiment: str
    response: str
    route_taken: str

def analyze_node(state: WorkflowState):
    """Execution node: Analyze the incoming query's sentiment."""
    logger.info(f"Analyzing query: {state['query']}")
    sentiment = analyze_sentiment(state["query"])
    return {"sentiment": sentiment}

def positive_handler(state: WorkflowState):
    """Handler for positive queries."""
    logger.info("Routing: Positive handler")
    reply = f"We're so glad to hear that! '{state['query']}' made our day."
    return {"response": reply, "route_taken": "positive_branch"}

def negative_handler(state: WorkflowState):
    """Handler for negative queries."""
    logger.info("Routing: Negative/Escalation handler")
    reply = f"I'm sorry you are experiencing this. We've escalated your issue regarding: '{state['query']}'."
    return {"response": reply, "route_taken": "negative_branch"}

def neutral_handler(state: WorkflowState):
    """Handler for neutral queries."""
    logger.info("Routing: Neutral handler")
    reply = f"Thank you for your message. Standard processing applied for: '{state['query']}'."
    return {"response": reply, "route_taken": "neutral_branch"}

def sentiment_router(state: WorkflowState):
    """Routing function for conditional edges."""
    logger.info(f"Conditional routing based on: {state['sentiment']}")
    return state["sentiment"]

# Define Graph
workflow = StateGraph(WorkflowState)

# Add Nodes
workflow.add_node("analyze_sentiment", analyze_node)
workflow.add_node("positive_branch", positive_handler)
workflow.add_node("negative_branch", negative_handler)
workflow.add_node("neutral_branch", neutral_handler)

# Setup Edges
workflow.set_entry_point("analyze_sentiment")
workflow.add_conditional_edges(
    "analyze_sentiment",
    sentiment_router,
    {
        "positive": "positive_branch",
        "negative": "negative_branch",
        "neutral": "neutral_branch"
    }
)

# Connect to End
for branch in ["positive_branch", "negative_branch", "neutral_branch"]:
    workflow.add_edge(branch, END)

# Compile
app_workflow = workflow.compile()
