# Bridge Builder Plan

## 1. What This Repo Is

Bridge is already a working prototype direction for an adaptive AAC assistant for non-verbal and minimally verbal children. The repo is not an empty scaffold. It has a FastAPI backend, a React/Vite frontend, database models, ML pipeline modules, sponsor integrations, and a dashboard-style product shell.

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
- MediaPipe, OpenAI, Whisper, Vapi, TinyFish, Nexla integration modules

Implemented routers:

- `children.py`: child profile create/list/get/update
- `intent.py`: frame/audio inference and WebSocket publishing
- `sessions.py`: sessions and child intent log retrieval
- `actions.py`: speak, IEP request, insurance appeal, sync session, journal, symbol prediction, intent confirmation
- `research.py`: AAC/IEP/insurance guidance assistant

Implemented ML/agent modules:

- `mediapipe_processor.py`: extracts pose and hand landmarks from base64 frames
- `audio_processor.py`: transcribes base64 audio with Whisper
- `intent_reasoner.py`: sends gesture/audio/profile/context to GPT-4o for ranked intent JSON
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

- `Dashboard.jsx`: overview, live communication teaser, journal, quick actions
- `ParentView.jsx`: camera capture, live intent predictions, WebSocket/API inference loop
- `SymbolBoard.jsx`: 4x4 AAC symbol grid, browser speech synthesis, Vapi call trigger
- `SessionLog.jsx`: progress charts and recent sessions, mostly mocked display data
- `ResearchPortal.jsx`: AAC guidance chat, IEP form, insurance appeal form, therapist search mock
- `Sidebar.jsx`: child profile selection and creation

### Infrastructure

Current local services:

- PostgreSQL in `docker-compose.dev.yml`
- Redis in `docker-compose.dev.yml`
- Backend Dockerfile under `infra/docker/Dockerfile.backend`

### Current Demo-Relevant Strengths

- The core app shape already matches the BridgeOS recommendation from `QnA.md`.
- The repo already contains more than three sponsor stories: Vapi, Redis, TinyFish, Nexla, Chainguard, and OpenAI.
- The live camera loop, symbol board, journal, and research portal create a coherent product demo.
- The database schema already supports child profiles, sessions, and intent logs.
- The backend already has the "learn from parent confirmation" concept through `/actions/confirm-intent`.

### Current Gaps And Risks

- Frontend API points at `http://127.0.0.1:4000`, while README says backend runs on `8000`.
- Backend returns intent fields as `probability`, but frontend `ParentView.jsx` reads `confidence`; live predictions can render as 0%.
- `api.fileIep` accepts grade and disability but only sends `child_id` and `school_district`; the form collects data that is not used.
- Dashboard and Session Log still rely heavily on mock data.
- Parent View does not yet show the strongest recommended demo elements: context selector, "why this prediction" reasoning, confirm button, and "give child a voice" action from the predicted intent.
- Symbol Board predicts symbols but does not expose context such as mealtime, bedtime, school, or therapy.
- Research Portal therapist search is a timed mock, not connected to TinyFish or a real search flow.
- Vapi integration uses a likely placeholder voice ID (`child-default`) and may need event-specific Vapi setup.
- TinyFish and Nexla calls are written as real integrations, but the exact event API contracts may differ.
- There is no polished 3-minute demo script or judge-facing architecture section in the app.
- There are minimal tests, and the existing `test_intent_reasoner.py` comment references Anthropic even though the code uses OpenAI.

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

The repo currently includes Vapi, Redis, TinyFish, Nexla, and Chainguard. It does not currently include WunderGraph, TigerData/Ghost, or InsForge.

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
- Dashboard updates recent event
- Symbol board moves Water, More, All Done, Help, Break to the top
- Journal/therapist summary includes the confirmed pattern
- Resource agent can draft an IEP/AAC support request

### Closing line

> Bridge does not replace parents or therapists. It gives them a shared language system that adapts to the child, so more children can be understood earlier, more often, and with more dignity.

## 6. Builder Plan

### Phase 0: Make The Existing App Demo-Stable

Priority: must do first.

Tasks:

- Fix frontend/backend port mismatch.
  - Either run backend on `4000`, or change `apps/web/src/api.js` to use `8000`.
  - Prefer a Vite env variable: `VITE_API_BASE=http://127.0.0.1:8000`.
- Normalize intent fields across backend and frontend.
  - Backend prompt currently returns `probability`.
  - Frontend currently reads `confidence`.
  - Pick one field name and support both defensively in the UI.
- Add graceful fallback behavior when OpenAI, Vapi, TinyFish, or Redis are missing.
  - For hackathon demo, the app should never hard-crash because one key is absent.
  - Show "demo mode" results where appropriate.
- Make startup instructions match reality.
  - README should state the same backend port that the frontend uses.
  - Add exact run commands for database, backend, and frontend.
- Run the frontend build and at least one backend smoke test.

Acceptance criteria:

- `GET /health` works.
- Child profile creation works.
- Dashboard loads after creating/selecting a child.
- Parent View can start camera without crashing.
- Inference results render non-zero percentages.
- Symbol Board can speak through browser speech synthesis even if Vapi fails.

### Phase 1: Build The Core BridgeOS Demo Loop

Priority: highest product value.

Tasks:

- Add a context selector to Parent View:
  - Mealtime
  - Bedtime
  - School
  - Therapy
- Send selected context to `/infer`.
- Show ranked intent cards with:
  - Label
  - Confidence/probability
  - Parent-friendly explanation
  - "Confirm" button
  - "Speak" button
- Wire "Confirm" to `/actions/confirm-intent`.
  - The backend requires `intent_log_id`, but `/infer` currently does not return it.
  - Update `/infer` to return the created log ID.
- Wire "Speak" from Parent View to `/actions/speak`.
  - Use the chosen intent label converted into a child-friendly phrase.
- After confirmation:
  - Update behavior profile
  - Refresh predicted symbols
  - Show a small "profile updated" event in the UI

Acceptance criteria:

- A judge can watch one flow from camera/frame input to ranked interpretation to parent confirmation to spoken output.
- The app visibly explains why the model suggested the top intent.
- The confirmed intent affects future profile/symbol behavior.

### Phase 2: Make The Adaptive Symbol Board Feel Intelligent

Priority: high.

Tasks:

- Add context awareness to Symbol Board.
  - If context is mealtime, prioritize Water, Snack, More, All Done, Help, Break.
  - If bedtime, prioritize Tired, Bathroom, Story, Light Off, Scared, Hug.
  - If school, prioritize Help, Break, Teacher, Loud, Finished, Bathroom.
  - If therapy, prioritize More, Stop, Help, Yes, No, Break.
- Add a "Suggested for right now" row above the full grid.
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
- Keep the 4x4 board stable for the demo, but allow the suggested row to change.

Acceptance criteria:

- The board visibly changes based on context and confirmed history.
- Parent can tap a symbol and hear it.
- Vapi failure does not block local speech output.

### Phase 3: Turn Dashboard And Session Log From Mocked To Real Enough

Priority: high for credibility.

Tasks:

- Replace hardcoded Dashboard stats with data from `/sessions/child/{child_id}/logs`.
- Compute:
  - Today's interaction count
  - Top intent today
  - Most-used symbol/intent
  - Recent confirmed pattern count
- Replace Session Log mock sessions with recent `IntentLog` data.
- Add a simple event timeline:
  - timestamp
  - top intent
  - confidence
  - confirmed label, if available
- Add a demo seed option if there is no data.
  - The app should still look alive in a judge demo.

Acceptance criteria:

- After running Parent View inference, Dashboard and Session Log update from persisted data.
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
- Add a button in Dashboard or Session Log:
  - "Generate therapist summary"
  - "Sync to therapist"
- Wire sync to existing Nexla endpoint if keys are available.
- Add demo fallback output if Nexla is unavailable.

Acceptance criteria:

- The demo shows Bridge helping both the parent and therapist.
- The summary uses actual logs where available.
- Nexla sponsor story is visible without becoming a blocker.

### Phase 5: Make Research Portal A Better Agent Moment

Priority: medium.

Current Research Portal already has:

- AAC guidance chat
- IEP request form
- Insurance appeal form
- Therapist search mock

Tasks:

- Make the portal explicitly show an "agent activity log":
  - "Reading child profile"
  - "Drafting request"
  - "Searching district portal"
  - "Preparing parent review"
- Pass grade and disability fields from frontend to backend for IEP requests.
- Add "review before submit" language.
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
- The TinyFish sponsor story is visible in the UI.

### Phase 6: Sponsor Tool Strategy

Priority: medium, but important for judging.

Already present:

- Vapi
- Redis
- TinyFish
- Nexla
- Chainguard
- OpenAI

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
  - OpenAI powers intent reasoning, symbol ranking, journal, and research guidance.

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
  - OpenAI
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

1. Fix port/config mismatch and intent field mismatch.
2. Make `/infer` return `intent_log_id`.
3. Add context selector to Parent View.
4. Add Confirm and Speak buttons to Parent View.
5. Wire confirmation into profile update.
6. Make Symbol Board context-aware.
7. Replace Dashboard/Session Log mocks with real log-derived data.
8. Add therapist summary.
9. Improve Research Portal agent activity log.
10. Add demo seed data and demo-mode fallbacks.
11. Update README and pitch script.
12. Run build/smoke tests.

## 8. Concrete Files To Touch

Likely frontend files:

- `apps/web/src/api.js`
- `apps/web/src/App.jsx`
- `apps/web/src/components/ParentView.jsx`
- `apps/web/src/components/SymbolBoard.jsx`
- `apps/web/src/components/Dashboard.jsx`
- `apps/web/src/components/SessionLog.jsx`
- `apps/web/src/components/ResearchPortal.jsx`
- `apps/web/src/App.css`

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
- Dashboard and therapist summaries need real confirmed data.
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
- Open Parent View
- Select mealtime
- Run inference or demo input
- See ranked possible intents with percentages
- Confirm top intent
- Speak phrase
- Open Symbol Board and see Water promoted
- Open Dashboard and see updated communication summary
- Open Research Portal and generate an IEP/AAC support draft

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
