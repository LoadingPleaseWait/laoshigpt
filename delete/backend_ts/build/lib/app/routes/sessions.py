from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter

from app.schemas.sessions import SessionStartRequest, SessionStartResponse

router = APIRouter()


@router.post("/start", response_model=SessionStartResponse)
def start_session(payload: SessionStartRequest) -> SessionStartResponse:
    return SessionStartResponse(
        session_id=f"sess_{uuid4().hex[:12]}",
        started_at=datetime.now(UTC),
        mode=payload.mode,
        scenario=payload.scenario,
    )
