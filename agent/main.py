import os
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from agent.models import AgentRequest, AgentResponse
from agent.graph import app as graph_app

# Ensure output directory exists
os.makedirs("output", exist_ok=True)

app = FastAPI(
    title="Autonomous AI Document Builder Agent API",
    description="FastAPI backend to autonomously design, plan, write, and review business documents.",
    version="1.0.0"
)

# Serve generated documents
app.mount("/output", StaticFiles(directory="output"), name="output")

@app.post("/agent", response_model=AgentResponse)
async def run_agent(payload: AgentRequest):
    if not payload.request.strip():
        raise HTTPException(status_code=400, detail="Request content cannot be empty.")
    
    # Initialize AgentState
    initial_state = {
        "request": payload.request,
        "plan": [],
        "current_step_index": 0,
        "current_draft": None,
        "step_retry_count": 0,
        "replan_count": 0,
        "assumptions": [],
        "sections": [],
        "review_status": "",
        "review_feedback": "",
        "docx_path": "",
        "logs": ["Initial state prepared. Starting agent graph..."]
    }
    
    try:
        final_state = graph_app.invoke(initial_state)
        
        return AgentResponse(
            request=final_state.get("request", ""),
            plan=final_state.get("plan", []),
            assumptions=final_state.get("assumptions", []),
            sections=final_state.get("sections", []),
            docx_path=final_state.get("docx_path", ""),
            logs=final_state.get("logs", []),
            success=True
        )
    except Exception as e:
        return AgentResponse(
            request=payload.request,
            plan=[],
            assumptions=[],
            sections=[],
            docx_path="",
            logs=["Agent failed during execution.", f"Error: {str(e)}"],
            success=False,
            error=str(e)
        )

@app.get("/download/{filename}")
async def download_file(filename: str):
    file_path = os.path.join("output", filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", filename=filename)
    raise HTTPException(status_code=404, detail="File not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
