from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.env import load_bridge_env

load_bridge_env()

from app.routers import intent, sessions, children, research, actions, vapi_webhooks
from app.routers.ghost_router import router as ghost_router
from app.core.database import init_db

app = FastAPI(title="Bridge AAC API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(intent.router)
app.include_router(sessions.router)
app.include_router(children.router)
app.include_router(research.router)
app.include_router(actions.router)
app.include_router(ghost_router)
app.include_router(vapi_webhooks.router)


@app.on_event("startup")
def on_startup():
    init_db()
    from app.integrations.ghost import init_pgmq
    init_pgmq()


@app.get("/health")
def health():
    return {"status": "ok"}
