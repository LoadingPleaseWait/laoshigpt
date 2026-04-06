# LaoshiGPT

LaoshiGPT is a Chinese conversation tutoring app focused on short daily speaking practice, immediate corrections, and retry-based learning.

## Repo structure (bootstrap)
- `frontend/` - React Native client (Expo)
- `backend/` - Backend API (LLM orchestration, persistence, analytics)
- `packages/shared-schemas/` - Shared response contracts and schema assets
- `docs/requirements/` - Product and architecture requirements
- `docs/plans/` - Implementation plans

## Product direction (MVP)
- HSK1-HSK2 learners
- Simplified Chinese only
- Text-only input
- 3 starter scenarios: food ordering, self-intro, directions
- Core loop: learner response -> correction -> retry -> review queue

## Implementation plan
See `docs/plans/2026-04-05-laoshigpt-mvp-bootstrap.md`.

## Scaffold status
- Frontend scaffold created in `frontend/` (Expo TypeScript layout + starter app)
- Backend scaffold created in `backend/` (FastAPI app + `/health`, `/v1/sessions/start`, `/v1/chat/turn`)
- Shared tutor schema created in `packages/shared-schemas/tutor-response.schema.json`

## Quick start
Backend:
- `cd backend`
- `python3 -m venv .venv && source .venv/bin/activate`
- `pip install -e .[dev]`
- `uvicorn app.main:app --reload`

Frontend:
- `cd frontend`
- `npm install`
- `npm run start`
