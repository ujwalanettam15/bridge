from sqlalchemy import Column, String, JSON, Float, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()


class Child(Base):
    __tablename__ = "children"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String)
    age = Column(Float)
    behavior_profile = Column(JSON, default={})
    preferred_symbols = Column(JSON, default=[])


class Session(Base):
    __tablename__ = "sessions"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    child_id = Column(String, ForeignKey("children.id"))
    started_at = Column(DateTime)
    intent_log = Column(JSON, default=[])


class IntentLog(Base):
    __tablename__ = "intent_logs"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    child_id = Column(String, ForeignKey("children.id"))
    timestamp = Column(DateTime)
    context = Column(JSON, default={})
    gesture_vector = Column(JSON)
    audio_transcript = Column(String)
    ranked_intents = Column(JSON)
    confirmed_label = Column(String)
    confirmed_at = Column(DateTime)
    spoken_phrase = Column(String)


class AgentRun(Base):
    __tablename__ = "agent_runs"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    child_id = Column(String, ForeignKey("children.id"))
    action_type = Column(String)
    status = Column(String)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    source_urls = Column(JSON, default=[])
    sources = Column(JSON, default=[])
    extracted_facts = Column(JSON, default=[])
    draft = Column(JSON, default={})
    pattern_summary = Column(JSON, default={})
    agent_steps = Column(JSON, default=[])
    sponsor_statuses = Column(JSON, default={})
    approvals = Column(JSON, default={})
