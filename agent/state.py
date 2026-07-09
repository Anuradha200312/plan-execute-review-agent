from typing import TypedDict, List, Dict, Any, Optional

class AgentState(TypedDict):
    request: str
    plan: List[Dict[str, str]]          # [{"step": "Step Title", "description": "Description"}]
    current_step_index: int
    current_draft: Optional[Dict[str, str]]       # {"heading": "...", "body": "..."}
    step_retry_count: int
    replan_count: int
    assumptions: List[str]
    sections: List[Dict[str, str]]      # List of approved {"heading": "...", "body": "..."}
    review_status: str                  # "approved" | "retry" | "replan" | ""
    docx_path: str
    logs: List[str]                     # To track decisions and steps for the Streamlit UI
