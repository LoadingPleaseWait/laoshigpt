# LaoshiGPT MVP Bootstrap Implementation Plan

> For Hermes: Use subagent-driven-development skill to implement this plan task-by-task.

Goal: bootstrap LaoshiGPT as a production-ready mobile tutoring app foundation (React Native client + backend API) centered on correction/retry learning loops.

Architecture: build a two-app repo with a React Native (Expo) mobile client and a FastAPI backend. Keep all LLM calls server-side, enforce strict JSON contracts, and persist user/session/correction data in Postgres. Start text-only and ship end-to-end scenario practice + review queue for beta.

Tech stack: React Native (Expo + TypeScript), FastAPI (Python), Postgres, SQLModel/SQLAlchemy + Alembic, Redis (optional queue/cache), OpenAPI + Pydantic schemas, provider abstraction for LLM/TTS.

---

## Product freeze for MVP v0.1
- HSK1-HSK2 only
- Simplified Chinese only
- Text input only (voice deferred)
- Default 10-minute sessions
- 3 scenarios: food ordering, self-intro, directions
- Free private beta

---

### Task 1: Repository scaffolding and standards
Objective: establish deterministic project layout and developer workflow.

Files:
- Create: `frontend/`
- Create: `backend/`
- Create: `packages/shared-schemas/`
- Create: `.editorconfig`, `.gitignore`, `README.md`, `Makefile`

Steps:
1) Initialize Expo TypeScript app in `frontend`.
2) Initialize Python backend in `backend` with uv/pip-tools/poetry (pick one and standardize).
3) Add root README with architecture diagram and local run commands.
4) Add lint/format scripts for both apps.
5) Commit: `chore: scaffold monorepo for mobile and api`

Verification:
- Mobile app starts successfully.
- API app boots with `/health` returning 200.

### Task 2: Shared response contract and schema validation
Objective: prevent UI breakage by enforcing strict tutor JSON response shape.

Files:
- Create: `packages/shared-schemas/tutor-response.schema.json`
- Create: `backend/app/schemas/tutor.py`
- Create: `frontend/src/types/tutor.ts`

Steps:
1) Define canonical fields: assistant_reply_zh, pinyin, english_translation, corrections[], vocabulary_highlights[], next_question, session_state.
2) Generate/align TypeScript and Python models from same contract.
3) Add API-side validator and fallback behavior for invalid model outputs.
4) Commit: `feat: add shared tutor response schema`

Verification:
- Contract tests pass for valid and invalid payloads.

### Task 3: Data model and migrations
Objective: create MVP persistence for sessions, turns, corrections, and review queue.

Files:
- Create: `backend/app/models/*.py`
- Create: `backend/alembic/versions/*_initial_schema.py`
- Create: `backend/app/db/session.py`

Steps:
1) Implement entities: User, LearningProfile, Session, MessageTurn, Correction, ReviewItem, AnalyticsEvent.
2) Add migrations and indexes for user_id/session_id/timestamps.
3) Add seed data for 3 scenarios and HSK constraints.
4) Commit: `feat: add core relational data model`

Verification:
- Migrations run cleanly on fresh DB.
- Seed command inserts scenario metadata.

### Task 4: Session lifecycle endpoints
Objective: support creating and resuming conversation sessions.

Files:
- Create: `backend/app/routes/sessions.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_sessions.py`

Steps:
1) Implement `POST /v1/sessions/start`.
2) Implement `POST /v1/sessions/end`.
3) Implement `GET /v1/sessions/{id}/history`.
4) Add auth placeholder middleware (JWT-compatible interface).
5) Commit: `feat: implement session lifecycle endpoints`

Verification:
- Tests validate start/end/history happy path and unauthorized access.

### Task 5: Tutor orchestrator and /v1/chat/turn
Objective: move notebook tutor loop into backend endpoint with persistent state.

Files:
- Create: `backend/app/services/tutor_orchestrator.py`
- Create: `backend/app/services/prompt_library.py`
- Create: `backend/app/services/llm_provider.py`
- Create: `backend/app/routes/chat.py`
- Create: `backend/tests/test_chat_turn.py`

Steps:
1) Build prompt templates by level + mode + scenario.
2) Implement provider abstraction with strict timeout/retry settings.
3) Validate model output against schema and apply fallback on failure.
4) Persist turn + corrections + session state metadata.
5) Commit: `feat: add turn processing endpoint with structured output`

Verification:
- End-to-end test confirms response fields and DB writes.
- Timeout test returns graceful retry action.

### Task 6: Correction retry tracking + review queue endpoints
Objective: complete the core learning loop and spaced review basics.

Files:
- Create: `backend/app/routes/review.py`
- Create: `backend/tests/test_review.py`
- Modify: chat/session services as needed

Steps:
1) Implement correction acceptance/retry tracking.
2) Implement `GET /v1/review/queue`.
3) Implement `POST /v1/review/submit`.
4) Promote corrected items to review queue with simple recency scheduling.
5) Commit: `feat: add correction retry and review queue APIs`

Verification:
- Retry events update correction status.
- Queue returns pending items and submit updates due dates/status.

### Task 7: Mobile app shell and navigation
Objective: create core app flow for onboarding and practice.

Files:
- Create: `frontend/src/screens/{Onboarding,ModeSelect,Practice,Review,Summary}.tsx`
- Create: `frontend/src/navigation/index.tsx`
- Create: `frontend/src/state/*`

Steps:
1) Implement navigation: Onboarding -> ModeSelect -> Practice -> Summary -> Review.
2) Capture learner level/goals in onboarding and persist locally.
3) Add API client with typed contracts.
4) Commit: `feat: add mobile shell and navigation flow`

Verification:
- Manual run reaches Practice screen in <= 2 taps for returning user.

### Task 8: Practice chat UI with correction/retry UX
Objective: deliver the differentiating learning interaction.

Files:
- Create: `frontend/src/components/{ChatTurn,CorrectionCard,RetryComposer}.tsx`
- Modify: `frontend/src/screens/Practice.tsx`
- Create: `frontend/src/tests/practice-flow.test.tsx`

Steps:
1) Render tutor turn package (zh/pinyin/translation/correction/next_question).
2) Add Try Again flow and submit improved sentence.
3) Visually acknowledge successful retry.
4) Add loading/retry/error states for timeout/failure.
5) Commit: `feat: implement correction and retry chat loop`

Verification:
- UI test covers original attempt -> correction -> retry -> accepted status.

### Task 9: Analytics and observability baseline
Objective: measure funnel and learning-loop quality from day one.

Files:
- Create: `backend/app/routes/analytics.py`
- Create: `backend/app/services/observability.py`
- Modify: mobile + api to emit events

Steps:
1) Track session_start/session_end/turn_submitted/correction_shown/correction_accepted/review_completed.
2) Capture latency, model/provider, prompt version, error code.
3) Add lightweight dashboard query doc in `docs/analytics/mvp-metrics.md`.
4) Commit: `feat: add mvp analytics instrumentation`

Verification:
- Event logs contain required fields and can reconstruct activation + retry rate.

### Task 10: Beta hardening and launch checklist
Objective: ensure app is safe, reliable, and ready for private beta.

Files:
- Create: `docs/release/beta-readiness-checklist.md`
- Create: `docs/privacy/data-retention.md`
- Modify: API/mobile configs for env separation

Steps:
1) Add privacy consent text + account deletion flow hooks.
2) Add rate limits and basic abuse controls on turn endpoint.
3) Run load/latency tests against P95 <= 4.0s target.
4) Prepare testflight/internal testing checklist.
5) Commit: `docs: add beta readiness and privacy checklist`

Verification:
- Acceptance checklist mapped to MVP acceptance criteria in requirements doc.

---

Execution order
1) Tasks 1-3 (foundation)
2) Tasks 4-6 (backend learning loop)
3) Tasks 7-8 (mobile UX)
4) Tasks 9-10 (measurement + hardening)

Definition of done (MVP)
- Must-have requirements from `docs/requirements/product-requirements-v0.1.txt` are implemented and test-verified.
- 3 scenarios work end-to-end.
- Correction -> retry -> review loop is functional and tracked.
- Session history and analytics are operational.
