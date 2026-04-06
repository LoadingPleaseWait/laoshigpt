from datetime import datetime

from pydantic import BaseModel


class SessionStartRequest(BaseModel):
    user_id: str
    mode: str
    scenario: str | None = None
    hsk_level: str


class SessionStartResponse(BaseModel):
    session_id: str
    started_at: datetime
    mode: str
    scenario: str | None = None
