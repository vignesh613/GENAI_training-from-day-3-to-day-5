from pydantic import BaseModel
from typing import Optional


class ReportRequest(BaseModel):
    topic: str


class ReportResponse(BaseModel):
    report_id: str
    status: str
    message: str = "Report generation started"


class ReportStatus(BaseModel):
    id: str
    topic: str
    status: str  # processing | completed | failed
    final_report: Optional[str] = None
    research_notes: Optional[str] = None
    revision_count: int = 0
    error: Optional[str] = None
