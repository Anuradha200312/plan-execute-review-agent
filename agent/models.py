from pydantic import BaseModel
from typing import List, Dict, Optional

class AgentRequest(BaseModel):
    request: str

class SectionModel(BaseModel):
    heading: str
    body: str

class StepModel(BaseModel):
    step: str
    description: str

class AgentResponse(BaseModel):
    request: str
    plan: List[StepModel]
    assumptions: List[str]
    sections: List[SectionModel]
    docx_path: str
    logs: List[str]
    success: bool
    error: Optional[str] = None
