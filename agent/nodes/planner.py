import json
from agent.state import AgentState
from agent.llm_client import call_llm

def planner_node(state: AgentState) -> AgentState:
    # If this is a replan (replan_count > 0), we want to provide the current feedback/failures/reasons to help revise
    is_replanning = state.get("replan_count", 0) > 0
    
    system_prompt = (
        "You are an autonomous AI Planner. Your job is to create a logical, ordered step-by-step "
        "document creation plan based on a user request. Each step must produce a specific section of the document.\n"
        "If the request lacks details (e.g. format, specific numbers, target audience, budget, timeline), "
        "you must make reasonable business assumptions and record them in the 'assumptions' array.\n"
        "Respond ONLY with a valid JSON object matching the following structure:\n"
        "{\n"
        "  \"plan\": [\n"
        "    {\"step\": \"Introduction\", \"description\": \"Drafts the introductory section including background.\"}\n"
        "  ],\n"
        "  \"assumptions\": [\n"
        "    \"Assumed target audience is general business stakeholders.\"\n"
        "  ]\n"
        "}"
    )
    
    user_prompt = f"User request: {state['request']}\n"
    if is_replanning:
        user_prompt += (
            f"\nThis is a REPLAN attempt (Current count: {state['replan_count']}).\n"
            f"The previous plan was: {json.dumps(state['plan'])}\n"
            f"The sections completed/approved so far: {json.dumps(state['sections'])}\n"
            f"The review verdict requested a replan with the following feedback:\n"
            f"\"{state.get('review_feedback', '')}\"\n"
            f"Please adjust the plan/steps to incorporate feedback or solve missing requirements."
        )
        
    log_msg = "Planning document structure..." if not is_replanning else f"Replanning document structure (attempt {state['replan_count']})..."
    state["logs"].append(log_msg)
    
    try:
        response_text = call_llm(system_prompt, user_prompt, json_mode=True)
        # Parse output
        parsed = json.loads(response_text)
        state["plan"] = parsed.get("plan", [])
        state["assumptions"] = parsed.get("assumptions", [])
        state["logs"].append(f"Generated plan with {len(state['plan'])} steps and {len(state['assumptions'])} assumptions.")
    except Exception as e:
        # Fallback in case LLM outputs invalid JSON or fails
        state["logs"].append(f"Planner failed: {str(e)}. Using a fallback outline.")
        state["plan"] = [
            {"step": "Executive Summary", "description": f"Executive summary of the proposal for: {state['request']}"},
            {"step": "Core Proposal Content", "description": f"Core details answering: {state['request']}"},
            {"step": "Conclusion", "description": "Concluding remarks and next steps."}
        ]
        state["assumptions"] = ["Assumed standard document structure due to parsing error."]
        
    return state
