from typing import TypedDict, Optional
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
import database
from models import ModerationStatus

class ModerationState(TypedDict):
    content_id: str
    text: str
    status: str
    moderation_reason: Optional[str]

# Nodes
def automate_moderation(state: ModerationState) -> ModerationState:
    text = state["text"].lower()
    # Simple mock model for moderation checks
    flagged_keywords = ["spam", "hate", "violence", "scam"]
    
    flagged = any(word in text for word in flagged_keywords)
    
    if flagged:
        state["status"] = ModerationStatus.HUMAN_REVIEW.value
        state["moderation_reason"] = "Automated check flagged potential policy violation."
    else:
        state["status"] = ModerationStatus.AUTO_APPROVED.value
    
    # Update DB
    item = database.get_content(state["content_id"])
    if item:
        item.status = ModerationStatus(state["status"])
        item.moderation_reason = state["moderation_reason"]
        database.save_content(item)
        
    return state

def publish(state: ModerationState) -> ModerationState:
    state["status"] = ModerationStatus.PUBLISHED.value
    
    # Update DB
    item = database.get_content(state["content_id"])
    if item:
        item.status = ModerationStatus.PUBLISHED
        database.save_content(item)
        
    return state

def human_review_node(state: ModerationState) -> ModerationState:
    # In a real app we might trigger an email or socket event here
    return state

# Routing logic
def route_after_moderation(state: ModerationState):
    if state["status"] == ModerationStatus.AUTO_APPROVED.value:
        return "publish"
    elif state["status"] == ModerationStatus.HUMAN_REVIEW.value:
        return "human_review_node"
        
def route_after_human(state: ModerationState):
    if state["status"] == ModerationStatus.APPROVED.value:
        return "publish"
    else:
        return END

# Build the Graph
workflow = StateGraph(ModerationState)

workflow.add_node("automate_moderation", automate_moderation)
workflow.add_node("human_review_node", human_review_node)
workflow.add_node("publish", publish)

workflow.add_edge(START, "automate_moderation")

workflow.add_conditional_edges(
    "automate_moderation",
    route_after_moderation,
    {"publish": "publish", "human_review_node": "human_review_node"}
)

workflow.add_conditional_edges(
    "human_review_node",
    route_after_human,
    {"publish": "publish", END: END}
)

workflow.add_edge("publish", END)

# In-memory checkpointer to resume human-in-the-loop
memory = MemorySaver()
app_graph = workflow.compile(checkpointer=memory, interrupt_before=["human_review_node"])
