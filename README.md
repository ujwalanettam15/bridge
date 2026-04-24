# Bridge

Bridge is an Augmentative and Alternative Communication (AAC) platform for parents of non-verbal and minimally verbal autistic children. It uses computer vision, audio processing, and AI to recognize what a child is trying to communicate through gestures, body language, and vocalizations — and helps families navigate administrative tasks like IEP requests and insurance appeals.

---

## What It Does

- **Real-time intent recognition** — captures video frames, extracts pose and hand landmarks, and classifies communication intents using AI
- **Adaptive behavior profiling** — learns each child's unique signals over time as parents confirm predictions
- **AAC symbol board** — predicts and displays the most likely communication symbols based on context and profile
- **Daily journal** — generates a parent-friendly summary of each day's communication
- **Administrative automation** — files IEP requests and insurance appeals on behalf of families using an autonomous AI agent
- **Therapist sync** — pushes session data to therapist webhooks for real-time collaboration
- **Research portal** — answers questions about IEP rights, insurance appeals, therapy options, and state-specific guidance

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
| AI / LLM | OpenAI SDK 1.51 — GPT-4o, Whisper |
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
| **OpenAI** (GPT-4o) | Intent classification, symbol prediction, journal generation, research Q&A | `OPENAI_API_KEY` |
| **OpenAI Whisper** | Audio transcription from video sessions | `OPENAI_API_KEY` |
| **VAPI** | Voice synthesis — speaks selected AAC symbols aloud | `VAPI_API_KEY` |
| **TinyFish AI** | Autonomous agent that files IEP requests and insurance appeals | `TINYFISH_API_KEY` |
| **Nexla** | Data flow platform — syncs session data to therapist webhooks | `NEXLA_API_KEY`, `NEXLA_FLOW_ID` |

---

## Running Locally

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
OPENAI_API_KEY=
VAPI_API_KEY=
TINYFISH_API_KEY=
NEXLA_API_KEY=
NEXLA_FLOW_ID=
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
│   │   │   │   ├── audio_processor.py       # Whisper audio transcription
│   │   │   │   ├── intent_reasoner.py       # GPT-4o intent classification
│   │   │   │   ├── symbol_predictor.py      # AAC symbol ranking
│   │   │   │   └── profile_updater.py       # Behavioral profile updates
│   │   │   ├── agents/
│   │   │   │   └── journal_agent.py         # Daily journal generation
│   │   │   └── integrations/
│   │   │       ├── vapi.py                  # VAPI voice synthesis
│   │   │       ├── tinyfish.py              # IEP & insurance appeal automation
│   │   │       └── nexla.py                 # Therapist data sync
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
│               └── ResearchPortal.jsx       # IEP/insurance guidance
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
2. OpenAI Whisper optionally transcribes any audio in the clip
3. GPT-4o classifies the intent using the landmark vectors, transcript, and the child's behavioral profile

A WebSocket endpoint (`/ws/intent/{child_id}`) streams live predictions as frames are captured every two seconds.

### Adaptive Profiling
Each child has a `behavior_profile` stored as JSON — confirmed intents, distinctive sounds, and hand signal patterns. When a parent confirms a prediction via `/confirm-intent`, the profile updates and feeds back into future inferences, personalizing accuracy over time.

### AAC Symbol Prediction
`/predict-symbols` ranks 16 predefined symbols (Snack, Water, Bathroom, Tired, Play, etc.) by likelihood, factoring in the child's profile, recent session history, and time of day.

### Administrative Automation
`/iep-request` and `/insurance-appeal` invoke a TinyFish AI agent that autonomously navigates school district portals and insurance claim systems, populating forms with the child's profile data.

### Daily Journal
`/journal/{child_id}` aggregates the day's intent logs and uses GPT-4o to produce a warm, jargon-free summary for parents.

### Therapist Sync
`/sync-session` triggers a Nexla flow that pushes structured session data to any configured therapist webhook endpoint.
