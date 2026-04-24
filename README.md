# Bridge

Bridge is an evidence-to-action care agent for AAC families. It helps parents confirm communication moments, speak the phrase locally, turn those moments into a structured evidence timeline, research real AAC/IEP sources, draft a parent-review support packet, and coordinate care-team follow-up only after approval.

---

## What It Does

- **Live Session** — suggests intents and lets the parent confirm what the child meant
- **Local AAC speech** — uses browser speech synthesis so the child phrase can be spoken immediately
- **Live Agent Memory** — publishes confirmed moments and agent stages through Redis
- **Evidence Timeline** — summarizes confirmed communication patterns parents can use in care conversations
- **Care Agent** — uses TinyFish open-web automation to extract facts from school/AAC sources and draft an AAC/IEP packet
- **Parent-approved follow-up** — syncs structured packet metadata through Nexla and prepares a Vapi care-team voice update only after approval
- **Audit trail** — stores agent runs, sources, drafts, approvals, and sponsor statuses in Postgres through `DATABASE_URL`

---

## Tech Stack

### Backend
| Layer | Technology |
|---|---|
| Framework | FastAPI 0.115 |
| Server | Uvicorn |
| Database | PostgreSQL 15 (SQLAlchemy 2.0, Alembic) |
| Cache / Pub-Sub | Redis 7 |
| Computer Vision | MediaPipe 0.10 (pose, hand, face landmarks) |
| AI / LLM | OpenRouter via OpenAI-compatible SDK |
| Async HTTP | httpx |
| Config | python-dotenv, Pydantic v2 |

### Frontend
| Layer | Technology |
|---|---|
| Framework | React 18 |
| Build Tool | Vite 4 |

### Infrastructure
| Layer | Technology |
|---|---|
| Containers | Docker (Chainguard hardened images) |
| Local Orchestration | docker-compose |

---

## External APIs

| Service | Purpose | Key |
|---|---|---|
| **OpenRouter** | Intent classification, symbol prediction, journal generation, research Q&A | `OPENROUTER_API_KEY` |
| **Vapi** | Parent-approved care-team voice update, not child TTS | `VAPI_API_KEY`, optional call config |
| **TinyFish AI** | Open-web source extraction for AAC/IEP packet drafting | `TINYFISH_API_KEY` |
| **Nexla Express** | Incoming Webhook source, Nexset generation, optional transforms/contracts, and delivery after approval | `NEXLA_INCOMING_WEBHOOK_URL` |
| **Ghost/Postgres** | Agent audit store through the normal database URL | `DATABASE_URL` |

---

## Running Locally

### One-command dev server

From the repo root:

```bash
npm run dev
```

This starts:

- Backend: `http://127.0.0.1:8000`
- Frontend: `http://127.0.0.1:5173`

The same command works on Windows and macOS. On macOS, the runner uses `python3` by default. If your Python command is different, run:

```bash
PYTHON=/path/to/python npm run dev
```

You can also build the frontend from the repo root:

```bash
npm run build
```

### Prerequisites
- Docker and docker-compose
- Python 3.11+
- Node.js 18+ and npm

### 1. Configure environment variables

Copy the example file and fill in your API keys:

```bash
cp .env.example .env
```

`.env.example`:
```
OPENROUTER_API_KEY=
OPENROUTER_MODEL=openrouter/free
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_REFERER=http://localhost:5173
OPENROUTER_TITLE=Bridge AAC
VAPI_API_KEY=
VAPI_PHONE_NUMBER_ID=
VAPI_ASSISTANT_ID=
VAPI_CUSTOMER_NUMBER=
TINYFISH_API_KEY=
NEXLA_INCOMING_WEBHOOK_URL=
NEXLA_EXPRESS_MCP_URL=https://veda-ai.nexla.io/mcp-express/
NEXLA_AUTH_HEADER=
DATABASE_URL=postgresql://postgres:bridge@localhost:5432/bridge
REDIS_URL=redis://localhost:6379
```

### 2. Start PostgreSQL and Redis

```bash
docker-compose -f docker-compose.dev.yml up -d
```

This starts:
- PostgreSQL 15 on `localhost:5432` (user: `postgres`, password: `bridge`, db: `bridge`)
- Redis 7 on `localhost:6379`

### 3. Start the backend

```bash
cd apps/backend
pip install -r requirements.txt
python -c "from app.core.database import init_db; init_db()"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`. You can verify it's running at `GET /health`.

### 4. Run database migrations

```bash
cd apps/backend
alembic upgrade head
```

### 5. Start the frontend

```bash
cd apps/web
npm install
npm run dev
```

The frontend will be available at `http://localhost:5173`.

---

## Project Structure

```
bridge/
├── apps/
│   ├── backend/
│   │   ├── app/
│   │   │   ├── main.py                  # FastAPI entry point
│   │   │   ├── models.py                # SQLAlchemy models
│   │   │   ├── routers/
│   │   │   │   ├── intent.py            # /infer — gesture→intent inference
│   │   │   │   ├── children.py          # Child profile CRUD
│   │   │   │   ├── sessions.py          # Session & intent log management
│   │   │   │   ├── actions.py           # Voice synthesis, IEP filing, symbol prediction
│   │   │   │   └── research.py          # Research/guidance AI endpoint
│   │   │   ├── ml/
│   │   │   │   ├── mediapipe_processor.py   # Pose & hand landmark extraction
│   │   │   │   ├── audio_processor.py       # Optional audio transcript hook
│   │   │   │   ├── intent_reasoner.py       # OpenRouter intent classification
│   │   │   │   ├── symbol_predictor.py      # AAC symbol ranking
│   │   │   │   └── profile_updater.py       # Behavioral profile updates
│   │   │   ├── agents/
│   │   │   │   └── journal_agent.py         # Daily journal generation
│   │   │   └── integrations/
│   │   │       ├── vapi.py                  # Parent-approved care-team voice updates
│   │   │       ├── tinyfish.py              # Open-web AAC/IEP source extraction
│   │   │       └── nexla.py                 # Nexla Express webhook delivery
│   │   ├── alembic/                         # Database migrations
│   │   └── requirements.txt
│   └── web/
│       └── src/
│           ├── App.jsx
│           ├── api.js
│           └── components/
│               ├── Dashboard.jsx            # Stats, journal, timeline
│               ├── ParentView.jsx           # Live camera + intent readout
│               ├── SymbolBoard.jsx          # AAC symbol grid
│               ├── SessionLog.jsx           # Past intent logs
│               ├── Sidebar.jsx              # Navigation & child selection
│               └── ResearchPortal.jsx       # Care Agent packet workflow
├── infra/
│   └── docker/
│       └── Dockerfile.backend              # Chainguard hardened multi-stage build
├── docker-compose.dev.yml
└── .env.example
```

---

## Key Technical Features

### Intent Inference Pipeline
Each inference request (`POST /infer`) processes a video frame through three stages:
1. MediaPipe extracts 33 pose landmarks and up to 21 hand landmarks per hand
2. Audio transcription is currently optional and returns a no-op fallback until a speech-to-text provider is added
3. OpenRouter classifies the intent using the landmark vectors, context, and the child's behavioral profile

A WebSocket endpoint (`/ws/intent/{child_id}`) streams live predictions as frames are captured every two seconds.

### Adaptive Profiling
Each child has a `behavior_profile` stored as JSON — confirmed intents, distinctive sounds, and hand signal patterns. When a parent confirms a prediction via `/confirm-intent`, the profile updates and feeds back into future inferences, personalizing accuracy over time.

### AAC Symbol Prediction
`/predict-symbols` ranks 16 predefined symbols (Snack, Water, Bathroom, Tired, Play, etc.) by likelihood, factoring in the child's profile, recent session history, and time of day.

### Care Agent
`/actions/iep-agent-run` reads confirmed communication history, extracts source facts through TinyFish when configured, drafts a parent-review AAC/IEP support packet, and saves an `AgentRun` audit record. When TinyFish credentials are absent or flaky, the endpoint returns honest demo-mode source facts so the judge demo remains reliable.

### Daily Journal
`/journal/{child_id}` aggregates the day's intent logs and uses OpenRouter to produce a warm, jargon-free summary for parents.

### Parent-Approved Follow-Up
`/actions/approve-care-followup` handles outbound action after parent approval. `nexla_sync` delivers structured packet metadata to a Nexla Express Incoming Webhook when `NEXLA_INCOMING_WEBHOOK_URL` is configured, or returns the prepared payload when it is not. `vapi_update` prepares or starts a care-team voice update through Vapi. Browser speech synthesis remains the local AAC voice for child-facing phrases.

### Nexla Express Setup
In Nexla, open **Integrate → Sources → Incoming Webhook** and create a webhook source for Bridge care packets. Let Nexla generate the source Nexset, optionally configure transforms/data contracts, then deliver the data to the chosen target. Put the generated incoming webhook URL in `.env` as `NEXLA_INCOMING_WEBHOOK_URL`.
