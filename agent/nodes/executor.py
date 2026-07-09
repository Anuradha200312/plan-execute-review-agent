import json
from agent.state import AgentState
from agent.llm_client import call_llm

def executor_node(state: AgentState) -> AgentState:
    idx = state["current_step_index"]
    step = state["plan"][idx]
    
    system_prompt = (
        "You are an AI Document Content Writer. Your task is to write detailed, professional, "
        "and well-structured content for a specific section of a document.\n"
        "Respond ONLY with a valid JSON object matching the following structure:\n"
        "{\n"
        "  \"heading\": \"Section Heading\",\n"
        "  \"body\": \"The detailed content/paragraphs for this section.\"\n"
        "}"
    )
    
    # Context of previously written sections and assumptions to ensure continuity
    context = ""
    if state["assumptions"]:
        context += "Assumptions made:\n" + "\n".join(f"- {a}" for a in state["assumptions"]) + "\n\n"
    if state["sections"]:
        context += "Previously written sections:\n"
        for s in state["sections"]:
            context += f"## {s['heading']}\n{s['body']}\n\n"
            
    user_prompt = (
        f"Original User Request: {state['request']}\n\n"
        f"{context}"
        f"Now, write the content for the current step:\n"
        f"Step Name: {step['step']}\n"
        f"Step Goal: {step['description']}\n"
    )
    
    if state["step_retry_count"] > 0:
        user_prompt += (
            f"\nNote: This is a retry attempt ({state['step_retry_count']}) for this step. "
            f"Please address the feedback or expand/improve the content based on the goals."
        )
        
    state["logs"].append(f"Executing step {idx+1}/{len(state['plan'])}: {step['step']}")
    
    try:
        response_text = call_llm(system_prompt, user_prompt, json_mode=True)
        parsed = json.loads(response_text)
        state["current_draft"] = {
            "heading": parsed.get("heading", step["step"]),
            "body": parsed.get("body", "")
        }
    except Exception as e:
        state["logs"].append(f"Executor failed: {str(e)}. Using fallback draft.")
        state["current_draft"] = {
            "heading": step["step"],
            "body": f"Draft content for {step['step']} addressing: {step['description']}."
        }
        
    return state
