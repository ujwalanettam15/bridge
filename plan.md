# Bridge Builder Plan

## 1. What This Repo Is

Bridge is already a working prototype direction for an adaptive AAC assistant for non-verbal and minimally verbal children. The repo is not an empty scaffold. It has a FastAPI backend, a React/Vite frontend, database models, ML pipeline modules, sponsor integrations, and a parent-first product shell.

The product thesis in the repo is:

> Bridge helps parents and therapists turn a child's gestures, sounds, context, and history into possible communication choices, then gives the child a voice through an adaptive symbol board.

The safest public positioning is not "AI understands non-verbal children." The better positioning is:

> Bridge is an adaptive AAC copilot that suggests possible intents, personalizes communication boards, and helps families and therapists respond faster.

This matters because the project touches children, disability, and health-adjacent data. The product should always frame model output as ranked possibilities for parent or therapist confirmation, not as certain diagnosis or mind-reading.

## 2. Current Repo State

### Backend

Location: `apps/backend`

Stack:

- FastAPI app in `app/main.py`
- SQLAlchemy models in `app/models.py`
- PostgreSQL via `app/core/database.py`
- Redis pub/sub via `app/core/redis_client.py`
- Alembic migration in `alembic/versions/001_initial.py`
- MediaPipe, OpenRouter, Vapi, TinyFish, Nexla integration modules

Implemented routers:

- `children.py`: child profile create/list/get/update
- `intent.py`: frame/audio inference and WebSocket publishing
- `sessions.py`: sessions and child intent log retrieval
- `actions.py`: speak, IEP request, insurance appeal, sync session, journal, symbol prediction, intent confirmation
- `research.py`: AAC/IEP/insurance guidance assistant

Implemented ML/agent modules:

- `mediapipe_processor.py`: extracts pose and hand landmarks from base64 frames
- `audio_processor.py`: optional audio transcript hook; currently no-ops until a speech-to-text provider is added
- `intent_reasoner.py`: sends gesture/audio/profile/context to OpenRouter for ranked intent JSON
- `symbol_predictor.py`: ranks likely AAC symbols from recent history and profile
- `profile_updater.py`: updates a child's behavior profile after a confirmed intent
- `journal_agent.py`: generates "Today I Felt" style parent journal summaries

Sponsor/integration modules:

- `vapi.py`: attempts to speak selected phrases through Vapi
- `tinyfish.py`: attempts IEP and insurance portal automation through TinyFish
- `nexla.py`: attempts therapist/session sync through Nexla
- `Dockerfile.backend`: uses Chainguard Python images

### Frontend

Location: `apps/web`

Stack:

- React 18
- Vite
- Plain CSS
- Fetch-based API client in `src/api.js`

Implemented product pages:

- `ParentView.jsx`: Live Session screen with context selection, camera capture, ranked intent suggestions, parent confirmation, and speech output
- `SymbolBoard.jsx`: Voice Board with a compact suggested-symbol row, 12 core AAC symbols, optional more symbols, browser speech synthesis, and Vapi call trigger
- `SessionLog.jsx`: History screen based on child intent logs rather than fake dashboard analytics
- `ResearchPortal.jsx`: Resources screen with AAC guidance chat and one selected parent-review task at a time for IEP, insurance, or therapist search
- `Sidebar.jsx`: child profile selection/creation and simplified primary nav

Removed from the primary UX:

- `Dashboard.jsx`
- fake communication scores
- fake session counts
- progress-percentage cards
- dense quick-action grids
- chart-heavy session mockups

### Infrastructure

Current local services:

- PostgreSQL in `docker-compose.dev.yml`
- Redis in `docker-compose.dev.yml`
- Backend Dockerfile under `infra/docker/Dockerfile.backend`

### Current Demo-Relevant Strengths

- The core app shape already matches the BridgeOS recommendation from `QnA.md`.
- The repo already contains more than three sponsor stories: Vapi, Redis, TinyFish, Nexla, Chainguard, and OpenRouter-routed LLMs.
- The live camera loop, voice board, history, and resources screens create a coherent product demo.
- The database schema already supports child profiles, sessions, and intent logs.
- The backend already has the "learn from parent confirmation" concept through `/actions/confirm-intent`.
- The frontend now defaults to the parent-facing Live Session flow instead of a broad dashboard.
- The UI has Bridge-specific metadata, favicon, and calmer visual styling instead of Vite defaults or generic AI-startup polish.
- The one-command root runner can start backend and frontend with `npm run dev` on Windows or macOS/Linux.

### Current Gaps And Risks

- Live demo quality still depends on having a running backend at `127.0.0.1:8000` and an available camera permission path.
- OpenRouter, Vapi, TinyFish, Nexla, Redis, and Postgres all need graceful demo-mode handling when keys/services are missing.
- Browser speech synthesis is a good fallback, but Vapi needs event-specific voice setup before relying on it live.
- The History screen reads real logs, but the demo still needs a reliable seed path so it does not look empty before the first inference.
- `api.fileIep` accepts grade and disability but only sends `child_id` and `school_district`; the form collects data that is not fully used by the backend yet.
- Resources therapist search is currently demo-mode, not connected to TinyFish or a real search flow.
- TinyFish and Nexla calls are written as real integrations, but the exact event API contracts may differ.
- There is no polished 3-minute demo script or judge-facing architecture screen in the app yet.
- There are minimal tests, and the LLM layer should stay provider-flexible through OpenRouter instead of direct model-provider wiring.

## 3. What The Research And QnA Recommend

`research.md` first recommends a caregiver operations agent for senior care because recent hackathon winners reward emotionally legible care workflows, real-world input, visible autonomy, and sponsor tool use.

`QnA.md` then evaluates the Bridge idea directly and says Bridge is the better move if it is narrowed sharply. The recommended build is not the full broad platform. The recommended build is:

> BridgeOS: an AI communication copilot for minimally verbal children.

The core recommendation:

- Keep the product focused on adaptive AAC.
- Show one strong loop instead of many half-finished features.
- Avoid claiming the AI fully understands a child.
- Use the AI to suggest possible intents, personalize a board, give the child a voice, update memory, summarize for therapists, and surface resources.

The recommended demo loop:

1. Parent selects a context: mealtime, bedtime, school, or therapy.
2. App analyzes a video/audio clip or live camera moment.
3. Agent combines context, recent history, child preferences, and gesture/audio signals.
4. App returns ranked possible intents with confidence and a parent-friendly explanation.
5. Parent confirms the intended meaning.
6. Vapi speaks the selected phrase as the child's voice.
7. System logs the event, updates the child's profile, refreshes the symbol board, generates a therapist summary, and optionally runs a resource/IEP/insurance action.

The recommended sponsor stack:

- Vapi: child voice output
- Redis: real-time session memory and pub/sub
- TinyFish: web automation for IEP, insurance, therapist/resource workflows
- WunderGraph: API/tool orchestration, if practical
- Ghost/TigerData: longitudinal interaction history, if available
- Chainguard: secure container story for sensitive child data
- Nexla: optional therapist/school data sync
- InsForge: optional backend/auth speed layer if easy

The repo currently includes Vapi, Redis, TinyFish, Nexla, Chainguard, and an OpenRouter-based LLM layer. It does not currently include WunderGraph, TigerData/Ghost, or InsForge.

## 3.1 OpenRouter LLM Plan

Bridge should use OpenRouter instead of direct OpenAI billing. Context7 confirms OpenRouter exposes an OpenAI-compatible chat completions API at:

> `https://openrouter.ai/api/v1`

The backend should keep using the `openai` Python package only as a compatible transport client, not as a direct OpenAI account dependency. Required env:

- `OPENROUTER_API_KEY`
- `OPENROUTER_MODEL`
- `OPENROUTER_BASE_URL`
- `OPENROUTER_REFERER`
- `OPENROUTER_TITLE`

Default model:

- `openrouter/free`

Reason:

- Context7 documents `openrouter/free` as OpenRouter's free-model router.
- The exact backing free model can change, so the model must remain configurable.
- If a specific model is needed for JSON reliability, set `OPENROUTER_MODEL` to that model ID during demo prep.

OpenRouter-backed features:

- Intent reasoning
- Symbol prediction
- Daily journal generation
- Research/IEP guidance Q&A

Not covered by OpenRouter:

- Speech-to-text transcription. The current audio processor should remain optional/no-op until a separate STT provider is chosen.

## 4. Product Decision

Build Bridge as:

> An adaptive AAC copilot for parents and therapists of minimally verbal children.

Do not build it as:

> A general autism understanding engine, medical diagnosis product, full therapy platform, or fully automated school/insurance filing system.

The highest-value hackathon version is:

- Live/session interpretation
- Parent confirmation
- Child voice output
- Adaptive symbol board
- Daily/therapist summary
- Resource/IEP/insurance agent
- Clear sponsor architecture

## 4.1 Implementation Status As Of April 24, 2026

Completed:

- Root `npm run dev` starts the backend and frontend together across Windows and macOS/Linux.
- Root `npm run build` builds the frontend from the repo root.
- Frontend API defaults to `http://127.0.0.1:8000`.
- LLM calls route through OpenRouter via `app/core/llm_client.py`.
- The app opens directly to Live Session.
- Primary nav is now:
  - Live Session
  - Voice Board
  - Resources
  - History
- Live Session has the core demo loop:
  - context selector
  - camera start/stop
  - ranked possible meanings
  - dominant top suggestion
  - Speak first, Confirm second
  - parent-review safety note
  - saved confirmation toast
- Voice Board shows top suggestions plus a stable 12-symbol core board.
- Resources shows one selected task at a time instead of three competing forms.
- History uses child logs and empty states instead of fake dashboard analytics.
- Old dashboard and Vite starter artifacts were removed.
- Visual style was simplified away from purple gradients, mock metrics, decorative clutter, and generic startup-site tells.

Verified:

- `npm run build` passes.
- Backend health check works when the backend is running.
- Browser smoke test was run on desktop and mobile after the UX cleanup.

Still needed before demo:

- Seed a reliable Maya demo profile and sample history.
- Confirm OpenRouter key/model behavior on the event network.
- Confirm Vapi voice configuration or rely on browser speech fallback.
- Validate TinyFish and Nexla event API contracts.
- Add a short architecture/pitch section for judges.
- Record a backup demo clip.

## 5. Demo Narrative

### Opening line

> For many minimally verbal children, the problem is not that they have nothing to say. It is that the world does not give them an easy way to say it.

### What Bridge does

> Bridge turns gestures, sounds, context, and family-confirmed history into ranked communication choices, then gives the child a voice through an adaptive AAC board.

### One clean demo

Use a sample child named Maya.

Context: mealtime.

Input: live camera or staged clip showing a reaching gesture and vocal stress.

Prediction:

- "I want water" - 72%
- "I need a break" - 18%
- "I want my toy" - 10%

Reason:

> Similar reaching pattern happened three times this week. Parent confirmed "water" twice during mealtime.

Action:

- Parent taps "Confirm water"
- App speaks: "I want water, please."
- History records the recent communication moment
- Symbol board moves Water, More, All Done, Help, Break to the top
- Journal/therapist summary includes the confirmed pattern
- Resource agent can draft an IEP/AAC support request

### Closing line

> Bridge does not replace parents or therapists. It gives them a shared language system that adapts to the child, so more children can be understood earlier, more often, and with more dignity.

## 6. Builder Plan

### Phase 0: Make The Existing App Demo-Stable

Status: mostly complete.

Priority: keep stable.

Tasks:

- Keep frontend/backend port config aligned.
  - Frontend defaults to `http://127.0.0.1:8000`.
  - `VITE_API_BASE` can override it.
- Keep intent fields normalized across backend and frontend.
  - UI should defensively support both `confidence` and `probability`.
- Add graceful fallback behavior when OpenRouter, Vapi, TinyFish, or Redis are missing.
  - For hackathon demo, the app should never hard-crash because one key is absent.
  - Show "demo mode" results where appropriate.
- Make startup instructions match reality.
  - README should state the same backend port that the frontend uses.
  - Add exact run commands for database, backend, and frontend.
- Run the frontend build and at least one backend smoke test.
- Route all LLM calls through `app/core/llm_client.py` so changing OpenRouter models is an env-only change.

Acceptance criteria:

- `GET /health` works.
- Child profile creation works.
- Live Session loads after creating/selecting a child.
- Live Session can start camera without crashing.
- Inference results render non-zero percentages.
- Voice Board can speak through browser speech synthesis even if Vapi fails.

### Phase 1: Build The Core BridgeOS Demo Loop

Status: implemented for frontend demo flow; keep hardening backend/demo-mode behavior.

Priority: highest product value.

Tasks:

- Maintain the context selector in Live Session:
  - Mealtime
  - Bedtime
  - School
  - Therapy
- Send selected context to `/infer`.
- Show ranked intent cards with:
  - Label
  - Confidence/probability
  - Parent-friendly explanation
  - "Speak" button
  - "Confirm" button
- Wire "Confirm" to `/actions/confirm-intent`.
  - The backend requires `intent_log_id`, but `/infer` currently does not return it.
  - Update `/infer` to return the created log ID.
- Keep "Speak" wired from Live Session to `/actions/speak`.
  - Use the chosen intent label converted into a child-friendly phrase.
- After confirmation:
  - Update behavior profile
  - Refresh predicted symbols
  - Show a small saved confirmation toast in the UI

Acceptance criteria:

- A judge can watch one flow from camera/frame input to ranked interpretation to parent confirmation to spoken output.
- The app visibly explains why the model suggested the top intent.
- The confirmed intent affects future profile/symbol behavior.

### Phase 2: Make The Voice Board Feel Intelligent

Status: partly implemented.

Priority: high.

Tasks:

- Add context awareness to Voice Board.
  - If context is mealtime, prioritize Water, Snack, More, All Done, Help, Break.
  - If bedtime, prioritize Tired, Bathroom, Story, Light Off, Scared, Hug.
  - If school, prioritize Help, Break, Teacher, Loud, Finished, Bathroom.
  - If therapy, prioritize More, Stop, Help, Yes, No, Break.
- Keep the "Suggested for right now" row above the core grid.
- Show why symbols were promoted:
  - "Mealtime context"
  - "Confirmed twice this week"
  - "Recently selected"
- Add missing useful AAC symbols:
  - No
  - Break
  - All Done
  - Too Loud
  - Different
  - Pain
- Keep the 12-symbol core board stable for the demo, with optional More symbols below it.

Acceptance criteria:

- The board visibly changes based on context and confirmed history.
- Parent can tap a symbol and hear it.
- Vapi failure does not block local speech output.

### Phase 3: Make History And Follow-Up Real Enough

Status: partly implemented.

Priority: high for credibility.

Tasks:

- Keep the old Dashboard out of the primary flow.
- Keep History focused on real `/sessions/child/{child_id}/logs` data.
- Compute:
  - Today's interaction count
  - Top intent today
  - Most-used symbol/intent
  - Recent confirmed pattern count
- Add or refine a simple event timeline:
  - timestamp
  - top intent
  - confidence
  - confirmed label, if available
- Add a demo seed option if there is no data.
  - The app should still look alive in a judge demo.

Acceptance criteria:

- After running Live Session inference, History updates from persisted data.
- Empty state is clean and demo-friendly.

### Phase 4: Strengthen The Journal And Therapist Summary

Priority: medium-high.

Tasks:

- Keep the parent-facing "Today I Felt" journal.
- Add a separate therapist summary format:
  - Observed communication attempts
  - Confirmed intents
  - Repeated patterns
  - Suggested symbol-board changes
  - Questions for next therapy session
- Add a button in History or Resources:
  - "Generate therapist summary"
  - "Sync to therapist"
- Wire sync to existing Nexla endpoint if keys are available.
- Add demo fallback output if Nexla is unavailable.

Acceptance criteria:

- The demo shows Bridge helping both the parent and therapist.
- The summary uses actual logs where available.
- Nexla sponsor story is visible without becoming a blocker.

### Phase 5: Make Resources A Better Agent Moment

Status: partly implemented.

Priority: medium.

Current Resources screen already has:

- AAC guidance chat
- IEP request form shown when selected
- Insurance appeal form shown when selected
- Therapist search currently shown as a demo-mode task when selected
- collapsed agent steps for TinyFish-style results

Tasks:

- Make the portal explicitly show an "agent activity log":
  - "Reading child profile"
  - "Drafting request"
  - "Searching district portal"
  - "Preparing parent review"
- Pass grade and disability fields from frontend to backend for IEP requests.
- Keep "review before submit" language.
  - For sensitive workflows, avoid implying unsupervised legal/education filing.
- Turn therapist search into either:
  - A TinyFish task, or
  - A clear demo-mode resource result with transparent labeling.
- Add one polished IEP output:
  - Subject line
  - Request body
  - Supporting rationale
  - Parent next steps

Acceptance criteria:

- The agent workflow looks autonomous and useful.
- The parent remains in control before submission.
- The TinyFish sponsor story is visible through behavior and agent steps without cluttering the UI.

### Phase 6: Sponsor Tool Strategy

Priority: medium, but important for judging.

Already present:

- Vapi
- Redis
- TinyFish
- Nexla
- Chainguard
- OpenRouter-routed LLMs

Potential additions:

- WunderGraph: only add if event setup makes it fast. Use it as an API orchestration layer for Bridge tools.
- TigerData/Ghost: only add if there is a simple managed Postgres/vector/time-series path. Otherwise, explain current Postgres event history and do not overbuild.
- InsForge: only add if it can replace or speed up auth/storage without destabilizing the repo.

Recommendation:

- Do not force every sponsor.
- Make 4-6 sponsor uses legible and reliable.
- The best visible sponsor story is:
  - Vapi gives the child a voice.
  - Redis streams live inference events.
  - TinyFish handles resource/IEP/insurance web tasks.
  - Nexla syncs therapy summaries.
  - Chainguard secures deployment.
  - OpenRouter powers intent reasoning, symbol ranking, journal, and research guidance while keeping model choice and cost flexible.

### Phase 7: Safety, Trust, And Wording

Priority: must have before demo.

Tasks:

- Add a small safety line near predictions:
  - "Bridge suggests possibilities for parent review. It does not diagnose or replace clinical judgment."
- Change any overclaiming language from "detects what they are saying" to "suggests possible intents."
- Add parent confirmation as the required step before the profile learns.
- Keep the product child-centered and dignity-preserving.
- Avoid saying "reads the child's mind" or "understands autism."

Acceptance criteria:

- The pitch feels ambitious without overclaiming.
- The UI makes clear that parents and therapists stay in control.

### Phase 8: Demo Polish

Priority: high after core loop works.

Tasks:

- Add a seeded demo child:
  - Name: Maya
  - Age: 6
  - Confirmed patterns: water during mealtime, break during loud moments, help during schoolwork
- Add demo data seeding endpoint or script.
- Add a "Demo Mode" toggle if API keys are missing.
- Add a polished architecture view or README section showing:
  - Frontend
  - FastAPI
  - MediaPipe
  - OpenRouter
  - Redis
  - PostgreSQL
  - Vapi
  - TinyFish
  - Nexla
  - Chainguard
- Prepare a 3-minute script.
- Record a backup screen capture in case live camera/API fails.

Acceptance criteria:

- The live demo can be completed in under 3 minutes.
- There is a backup path for flaky APIs.
- The sponsor story is obvious without needing a long explanation.

## 7. Suggested Implementation Order

1. Keep `npm run build` and `npm run dev` working from the repo root.
2. Add demo seed data for Maya and a reliable "reset demo" path.
3. Confirm `/infer` always returns `intent_log_id`, normalized confidence values, and context.
4. Harden OpenRouter fallback responses for event-network/API-key failures.
5. Finalize Vapi voice configuration, with browser speech synthesis as fallback.
6. Make Voice Board context/history promotion reasons visible but compact.
7. Add therapist summary generation from real logs.
8. Connect therapist search to TinyFish or label it clearly as demo-mode.
9. Pass grade and disability fields through IEP request APIs.
10. Add judge-facing architecture/pitch content.
11. Validate sponsor services: Redis, Vapi, TinyFish, Nexla, Chainguard, OpenRouter.
12. Run build, backend health, desktop/mobile browser smoke tests, and record a backup demo.

## 8. Concrete Files To Touch

Likely frontend files:

- `apps/web/src/api.js`
- `apps/web/src/App.jsx`
- `apps/web/src/components/ParentView.jsx`
- `apps/web/src/components/SymbolBoard.jsx`
- `apps/web/src/components/SessionLog.jsx`
- `apps/web/src/components/ResearchPortal.jsx`
- `apps/web/src/components/Sidebar.jsx`
- `apps/web/src/index.css`
- `apps/web/index.html`
- `apps/web/public/bridge-mark.svg`

Likely backend files:

- `apps/backend/app/routers/intent.py`
- `apps/backend/app/routers/actions.py`
- `apps/backend/app/routers/sessions.py`
- `apps/backend/app/ml/intent_reasoner.py`
- `apps/backend/app/ml/symbol_predictor.py`
- `apps/backend/app/agents/journal_agent.py`
- `apps/backend/app/models.py`
- `apps/backend/alembic/versions/001_initial.py` or a new migration

Likely docs/config:

- `README.md`
- `.env.example`
- `docker-compose.dev.yml`
- `infra/docker/Dockerfile.backend`

## 9. Data Model Improvements

Current tables are enough for a prototype, but the demo would benefit from a few fields:

### `IntentLog`

Add:

- `context`
- `confirmed_label`
- `confirmed_at`
- `spoken_phrase`

Reason:

- Parent confirmation needs to persist.
- History and therapist summaries need real confirmed data.
- Context is central to the BridgeOS story.

### `Child`

Current fields are enough:

- `behavior_profile`
- `preferred_symbols`

Do not over-model child profiles unless needed. JSON is fine for hackathon speed.

### `Session`

Current session model is minimal. It can stay minimal unless the app needs start/end/duration in the UI.

Potential additions:

- `ended_at`
- `context`
- `summary`

## 10. API Improvements

### `POST /infer`

Current:

- Accepts child ID, frame, audio, context
- Logs result
- Publishes to Redis
- Returns model result

Change:

- Return `intent_log_id`
- Normalize fields to `confidence`
- Include context in log
- Handle missing child with 404
- Return fallback demo result when configured for demo mode

### `POST /actions/confirm-intent`

Current:

- Updates child profile from a confirmed intent

Change:

- Store `confirmed_label` and `confirmed_at` on the intent log
- Return updated behavior profile summary
- Return suggested symbols if easy

### `POST /actions/predict-symbols`

Current:

- Predicts symbols from profile and recent intents

Change:

- Accept context
- Return objects, not just names:
  - `label`
  - `score`
  - `reason`

### `GET /sessions/child/{child_id}/logs`

Current:

- Returns raw logs

Change:

- Keep raw endpoint, but optionally add a summary endpoint:
  - `/sessions/child/{child_id}/summary`

## 11. Testing Plan

Minimum tests/smoke checks:

- Backend import/startup check
- `GET /health`
- child create/list
- MediaPipe synthetic frame script
- intent reasoner mock or demo-mode result
- symbol prediction fallback
- frontend build

Manual demo checklist:

- Add/select Maya profile
- Open Live Session
- Select mealtime
- Run inference or demo input
- See ranked possible intents with percentages
- Confirm top intent
- Speak phrase
- Open Voice Board and see Water promoted
- Open History and see the communication moment
- Open Resources and generate an IEP/AAC support draft

## 12. Pitch Checklist

The final pitch should show:

- Human problem in one sentence
- Live product loop in under 90 seconds
- Parent confirmation and child voice moment
- Adaptive board update
- Therapist/resource follow-through
- Sponsor architecture mapped to visible product behavior
- Responsible safety framing

Avoid:

- Long architecture-first explanation
- Too many tabs
- Claims that the AI knows the child's true intent
- Unreviewed legal/medical automation claims

## 13. Final Build Target

The target for this repo should be:

> A polished demo where a parent selects context, Bridge suggests possible intents from camera/audio/history, the parent confirms one, Bridge speaks it for the child, updates the adaptive board, and generates a useful caregiver/therapist follow-up.

That is the version that best matches the existing codebase, the `QnA.md` recommendation, and the hackathon pattern described in `research.md`.
