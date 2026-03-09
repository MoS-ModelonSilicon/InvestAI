from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


class SuggestionCreate(BaseModel):
    message: str
    category: str = "feature"  # feature/bug/improvement/content


class SuggestionOut(BaseModel):
    id: int
    user_id: int
    message: str
    ai_summary: str
    category: str
    status: str
    admin_notes: str
    votes: int
    github_issue_url: str = ""
    github_issue_number: int | None = None
    created_at: datetime | None
    user_email: str = ""

    class Config:
        from_attributes = True


class SuggestionUpdateStatus(BaseModel):
    status: str  # new/reviewed/planned/done/declined
    admin_notes: Optional[str] = None
