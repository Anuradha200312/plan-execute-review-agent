import json
from agent.state import AgentState
from agent.llm_client import call_llm

def reviewer_node(state: AgentState) -> AgentState:
    idx = state["current_step_index"]
    step = state["plan"][idx]
    draft = state["current_draft"]
    
    system_prompt = (
        "You are an AI Document Reviewer. Your role is to critically evaluate a drafted section "
        "against the step's goal and the user's original request.\n"
        "You must determine if it is ready to be approved, if it needs a retry (re-writing), "
        "or if the entire planning structure is missing something essential (requires replanning).\n"
        "Respond ONLY with a valid JSON object matching the following structure:\n"
        "{\n"
        "  \"approved\": true,\n"
        "  \"reason\": \"retry\" or \"replan\" or \"\",\n"
        "  \"feedback\": \"Feedback explaining your decision.\"\n"
        "}"
    )
    
    user_prompt = (
        f"Original User Request: {state['request']}\n"
        f"Step Name: {step['step']}\n"
        f"Step Goal: {step['description']}\n\n"
        f"Draft Heading: {draft['heading']}\n"
        f"Draft Body:\n{draft['body']}\n\n"
        "Determine if this draft meets the requirements. If it lacks detail or is off-topic, "
        "mark approved=false and reason='retry'. If it reveals that the plan itself is missing "
        "essential sections or structured incorrectly to satisfy the user request, mark approved=false and reason='replan'."
    )
    
    state["logs"].append(f"Reviewing draft for step: {step['step']}")
    
    try:
        response_text = call_llm(system_prompt, user_prompt, json_mode=True)
        parsed = json.loads(response_text)
        
        approved = parsed.get("approved", True)
        reason = parsed.get("reason", "")
        feedback = parsed.get("feedback", "")
        
        if approved:
            state["review_status"] = "approved"
            state["review_feedback"] = ""
            state["logs"].append(f"Review SUCCESS: Step '{step['step']}' approved. {feedback}")
            state["sections"].append(state["current_draft"])
            state["current_step_index"] += 1
            state["step_retry_count"] = 0
        else:
            status = "replan" if reason == "replan" else "retry"
            state["review_status"] = status
            state["review_feedback"] = feedback
            state["logs"].append(f"Review FAILURE ({status.upper()}): {feedback}")
            
            if status == "retry":
                if state["step_retry_count"] < 2:
                    state["step_retry_count"] += 1
                else:
                    state["logs"].append("Max retry count (2) exceeded. Accepting best-effort draft and proceeding.")
                    state["sections"].append(state["current_draft"])
                    state["current_step_index"] += 1
                    state["step_retry_count"] = 0
                    state["review_status"] = "approved" # Override status to proceed
            elif status == "replan":
                if state["replan_count"] < 2:
                    state["replan_count"] += 1
                else:
                    state["logs"].append("Max replan count (2) exceeded. Continuing with the current plan structure.")
                    state["sections"].append(state["current_draft"])
                    state["current_step_index"] += 1
                    state["step_retry_count"] = 0
                    state["review_status"] = "approved" # Override status to proceed
    except Exception as e:
        state["logs"].append(f"Reviewer node failed: {str(e)}. Approving by default to prevent stuck states.")
        state["review_status"] = "approved"
        state["sections"].append(state["current_draft"])
        state["current_step_index"] += 1
        state["step_retry_count"] = 0
        
    return state
