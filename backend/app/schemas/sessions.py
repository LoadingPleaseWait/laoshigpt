from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SessionStartRequest(BaseModel):
    user_id: str
    mode: str
    scenario: Optional[str] = None
    hsk_level: str


class SessionStartResponse(BaseModel):
    session_id: str
    started_at: datetime
    mode: str
    scenario: Optional[str] = None
