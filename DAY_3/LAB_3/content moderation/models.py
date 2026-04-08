from pydantic import BaseModel
from typing import Optional
from enum import Enum

class ModerationStatus(str, Enum):
    PENDING = "PENDING"
    AUTO_APPROVED = "AUTO_APPROVED"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PUBLISHED = "PUBLISHED"

class ContentItem(BaseModel):
    id: str
    text: str
    status: ModerationStatus = ModerationStatus.PENDING
    moderation_reason: Optional[str] = None
    
class SubmitRequest(BaseModel):
    text: str
    
class ApprovalRequest(BaseModel):
    note: Optional[str] = ""
