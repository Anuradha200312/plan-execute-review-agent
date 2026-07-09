from langgraph.graph import StateGraph, END
from agent.state import AgentState
from agent.nodes.planner import planner_node
from agent.nodes.executor import executor_node
from agent.nodes.reviewer import reviewer_node
from agent.nodes.doc_builder import doc_builder_node

def route_after_review(state: AgentState) -> str:
    """
    Decides where to route next based on the review status of the current step.
    Note that reviewer_node handles mutations like appending drafts to sections and incrementing indexes/counts.
    """
    status = state.get("review_status", "approved")
    
    if status == "replan":
        return "planner"
    elif status == "retry":
        return "executor"
    else:  # approved or fallback
        idx = state["current_step_index"]
        plan_len = len(state.get("plan", []))
        if idx < plan_len:
            return "executor"
        else:
            return "doc_builder"

# Initialize graph
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("planner", planner_node)
workflow.add_node("executor", executor_node)
workflow.add_node("reviewer", reviewer_node)
workflow.add_node("doc_builder", doc_builder_node)

# Set entry point
workflow.set_entry_point("planner")

# Add transitions
workflow.add_edge("planner", "executor")
workflow.add_edge("executor", "reviewer")
workflow.add_conditional_edges("reviewer", route_after_review)
workflow.add_edge("doc_builder", END)

# Compile
app = workflow.compile()
