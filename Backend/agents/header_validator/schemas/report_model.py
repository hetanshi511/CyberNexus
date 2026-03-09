from pydantic import BaseModel
from typing import List, Optional

class MissingHeader(BaseModel):
    name: str
    description: str

class PresentHeader(BaseModel):
    name: str
    value: str

class UpcomingHeader(BaseModel):
    name: str
    value: Optional[str] = None
    present: bool
    description: str
    
class SecurityIssue(BaseModel):
    category: str
    issues: List[str]

class HeaderReportResponse(BaseModel):
    site: str
    ip_address: str
    report_time: str
    status_code: int
    security_score: int
    grade: str
    present_security_headers: List[PresentHeader]
    missing_headers: List[MissingHeader]
    upcoming_headers: List[UpcomingHeader]
    security_issues: List[SecurityIssue]
    raw_headers: List[PresentHeader]
    llm_analysis: str
