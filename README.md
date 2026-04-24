# Bridge

Bridge is an evidence-to-action care agent for AAC families.

It helps a parent, teacher, or caregiver turn confirmed communication moments into shared documentation: a live AAC phrase, an evidence timeline, a teacher daily update, a source-grounded AAC/IEP support packet, and parent-approved follow-up.

The demo story is simple:

```text
Confirm Maya's communication moment
-> stream it through Live Agent Memory
-> collect a teacher update by voice
-> add school evidence to the timeline
-> research real AAC/IEP sources
-> draft a parent-review support packet
-> approve Nexla/Vapi follow-up
```

Bridge does not diagnose, replace therapists, or automatically contact schools. The adult confirms every communication moment and approves every outbound action.

## Why It Matters

Parents and teachers often understand individual moments: a child wants water, needs help, asks for a comfort item, or reacts to noise. The harder problem is that these moments get lost before they can become useful evidence for school and care-team support.

Bridge turns those moments into a structured record families can actually use.

## Demo Highlights

- **Live Session**: camera-assisted suggested intents for Maya, with parent confirmation as the required step.
- **Local AAC speech**: browser speech synthesis speaks the phrase immediately; Vapi is not used as child TTS.
- **Visual cue detection**: OpenCV detects demo props such as a gray bottle or dark hat and boosts the relevant intent.
- **Live Agent Memory**: Redis-style event stream shows confirmations and agent stages in real time.
- **Evidence Timeline**: varied home and school moments become a pattern summary.
- **Teacher Daily Update**: Vapi calls the teacher/caregiver after parent approval, receives transcript/end-of-call events, and Bridge generates a mini-report.
- **Care Agent**: TinyFish open-web extraction grounds the AAC/IEP packet in real SFUSD and California assistive technology sources.
- **Parent approvals**: Nexla delivery and Vapi care-team voice updates only happen after review.
- **Audit trail**: Ghost/Postgres stores agent runs, source facts, drafts, transcripts, approvals, and sponsor statuses.
- **Presentation Autopilot**: a guided demo mode walks through the full story while the presenter speaks.

## Sponsor Roles

| Sponsor | What Bridge Uses It For |
|---|---|
| **Vapi** | Parent-approved outbound teacher/caregiver calls and care-team voice updates |
| **Redis** | Live Agent Memory/event stream for confirmations and agent stages |
| **TinyFish** | Open-web source extraction from school/AAC/assistive technology resources |
| **Nexla Express** | Approved structured delivery through an Incoming Webhook flow |
| **Ghost / TigerData** | Managed Postgres audit store, durable queue records, and DB-backed agent state |
| **Chainguard** | Secure/minimal backend container story in `infra/docker/Dockerfile.backend` |

## Tech Stack

| Area | Stack |
|---|---|
| Frontend | React 18, Vite |
| Backend | FastAPI, Uvicorn, SQLAlchemy |
| Database | Postgres via `DATABASE_URL` |
| Real-time memory | Redis |
| Vision | MediaPipe landmarks plus OpenCV color/shape detection |
| LLM-compatible API | OpenRouter for non-vision helper tasks when configured |
| Voice | Vapi outbound calls |
| Web automation | TinyFish |
| Data delivery | Nexla Express Incoming Webhook |

## Project Structure

```text
bridge/
apps/
  backend/
    app/
      agents/              # journal + teacher update report logic
      core/                # DB, env, Redis/event helpers
      integrations/        # Vapi, TinyFish, Nexla, Ghost
      ml/                  # MediaPipe/OpenCV intent support
      routers/             # FastAPI routes + webhooks
      models.py            # Child, IntentLog, AgentRun
    requirements.txt
  web/
    src/
      App.jsx              # routes + autopilot demo controller
      api.js
      components/
        ParentView.jsx     # Live Session
        SessionLog.jsx     # Evidence Timeline
        ResearchPortal.jsx # Care Agent
        SymbolBoard.jsx    # Voice Board
infra/docker/Dockerfile.backend
scripts/dev.mjs
docker-compose.dev.yml
plan.md
DEVPOST.md
```

## Running Locally

Prerequisites:

- Node.js 18+
- Python 3.10+
- Docker Desktop, if you want local Postgres/Redis

Install frontend dependencies:

```bash
npm run install:web
```

Start Postgres and Redis:

```bash
docker compose -f docker-compose.dev.yml up -d
```

Start frontend and backend together:

```bash
npm run dev
```

URLs:

- Frontend: `http://127.0.0.1:5173`
- Backend health: `http://127.0.0.1:8000/health`

Build check:

```bash
npm run build
python -m compileall apps/backend/app
```

## Environment

Copy `.env.example` to `.env` and fill in the services you want live. Bridge still has prepared/replay fallbacks for demo reliability when a sponsor key is missing.

```env
DATABASE_URL=postgresql://postgres:bridge@localhost:5432/bridge
REDIS_URL=redis://localhost:6379

OPENROUTER_API_KEY=
OPENROUTER_MODEL=openrouter/free
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

VAPI_API_KEY=
VAPI_PHONE_NUMBER_ID=
VAPI_ASSISTANT_ID=
VAPI_TEACHER_ASSISTANT_ID=
VAPI_CUSTOMER_NUMBER=
VAPI_SERVER_URL=

TINYFISH_API_KEY=
NEXLA_INCOMING_WEBHOOK_URL=

GHOST_API_KEY=
GHOST_DATABASE_NAME=bridge-prod
GHOST_ENABLE_FORKS=false
```

## Vapi Teacher Call Webhooks

For live Vapi transcript callbacks while developing locally, expose the backend with Cloudflare Tunnel or ngrok.

Cloudflare example:

```powershell
cloudflared tunnel --url http://127.0.0.1:8000
```

Set the resulting URL in `.env`:

```env
VAPI_SERVER_URL=https://your-tunnel.trycloudflare.com/webhooks/vapi
```

In the Vapi teacher assistant, use the same server/webhook URL and enable:

```text
status-update
transcript
end-of-call-report
conversation-update
```

Bridge uses `VAPI_TEACHER_ASSISTANT_ID` for teacher update calls and falls back to `VAPI_ASSISTANT_ID` if a separate teacher assistant is not configured.

## Main API Routes

| Route | Purpose |
|---|---|
| `POST /sessions/seed-maya-demo` | Reset and seed the Maya demo profile/evidence |
| `POST /infer` | Analyze a camera frame and return suggested intents |
| `POST /actions/demo-confirm-intent` | Demo-safe parent confirmation without camera dependency |
| `POST /actions/request-teacher-update` | Start/replay teacher daily update flow |
| `GET /actions/teacher-updates/{child_id}` | Fetch teacher mini-reports |
| `POST /webhooks/vapi` | Receive Vapi status/transcript/end-of-call callbacks |
| `POST /actions/iep-agent-run` | Generate the AAC/IEP support packet |
| `POST /actions/approve-care-followup` | Approve Nexla or Vapi outbound follow-up |
| `GET /actions/agent-events/{child_id}` | Replay Live Agent Memory events |
| `GET /ghost/status` | Surface Ghost/Postgres audit-store status |

## Demo Script Framing

Bridge should be demoed as:

> Watch Bridge turn one parent-confirmed communication moment into evidence, documentation, and follow-up.

Not as:

> Watch AI magically understand this child.

The strongest safety point is that Bridge keeps the parent in control. It suggests, organizes, researches, drafts, and routes, but it does not diagnose or send anything without review.

## Verification

Current repo checks:

```bash
npm run build
python -m compileall apps/backend/app
```

