import os

import openai

OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/free")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

_headers = {}
if os.getenv("OPENROUTER_REFERER"):
    _headers["HTTP-Referer"] = os.getenv("OPENROUTER_REFERER")
if os.getenv("OPENROUTER_TITLE"):
    _headers["X-OpenRouter-Title"] = os.getenv("OPENROUTER_TITLE")

client = openai.AsyncOpenAI(
    base_url=OPENROUTER_BASE_URL,
    api_key=OPENROUTER_API_KEY or "demo",
    default_headers=_headers or None,
)


def llm_configured() -> bool:
    return bool(OPENROUTER_API_KEY)


def chat_model() -> str:
    return os.getenv("OPENROUTER_MODEL", OPENROUTER_MODEL)
