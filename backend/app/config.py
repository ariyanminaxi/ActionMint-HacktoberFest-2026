from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")
load_dotenv(ROOT / "model" / ".env.model")


KNOWN_PROVIDERS = ("gemini", "groq", "ollama", "mock")
DEV_TOKEN = "dev-token-change-me"


def _list(name: str, default: str) -> tuple[str, ...]:
    return tuple(x.strip() for x in os.getenv(name, default).split(",") if x.strip())


def _provider_chain(name: str, default: str) -> tuple[str, ...]:
    """Keep only providers this build implements.

    A stale `.env` may still name a removed provider (kaggle, droplet). Dropping the name here
    means such a file can never re-enable dead code or leave the chain unbuildable.
    """
    requested = tuple(x.strip().lower() for x in _list(name, default))
    kept = tuple(provider for provider in requested if provider in KNOWN_PROVIDERS)
    return kept or ("mock",)


ENV = os.getenv("ENV", "dev").strip() or "dev"
# In development an empty APP_TOKEN would reject every request, including the UI's demo token.
APP_TOKEN = os.getenv("APP_TOKEN", "").strip() or (DEV_TOKEN if ENV == "dev" else "")


@dataclass(frozen=True)
class Settings:
    env: str = ENV
    app_token: str = APP_TOKEN
    allowed_origins: tuple[str, ...] = _list("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    provider_chain: tuple[str, ...] = _provider_chain("PROVIDER_CHAIN", "gemini,groq,ollama,mock")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemma-4-26b-a4b-it")
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_model: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
    groq_base_url: str = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    ollama_url: str = os.getenv("OLLAMA_URL", "http://localhost:11434/v1")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "gemma4:e2b")
    stt_backend: str = os.getenv("STT_BACKEND", "mock")
    stt_model: str = os.getenv("STT_MODEL", "base")
    max_media_mb: int = int(os.getenv("MAX_MEDIA_MB", "10"))
    max_media_min: int = int(os.getenv("MAX_MEDIA_MIN", "5"))
    max_transcript_chars: int = 60000
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_service_key: str = os.getenv("SUPABASE_SERVICE_KEY", "")
    bot_backend: str = os.getenv("BOT_BACKEND", "simulated")
    bot_name: str = os.getenv("BOT_NAME", "Meeting Notes Bot (AI)")
    bot_platforms: tuple[str, ...] = _list("BOT_PLATFORMS", "meet")
    bot_api_key: str = os.getenv("BOT_API_KEY", "")
    bot_api_base: str = os.getenv("BOT_API_BASE", "")
    bot_worker_url: str = os.getenv("BOT_WORKER_URL", "")
    bot_worker_secret: str = os.getenv("BOT_WORKER_SECRET", "")
    bot_webhook_secret: str = os.getenv("BOT_WEBHOOK_SECRET", "")
    frontend_api_base: str = os.getenv("VITE_API_BASE", "http://localhost:8000")

    def model_for(self, provider: str) -> str:
        return {"gemini": self.gemini_model, "groq": self.groq_model, "ollama": self.ollama_model}.get(provider, self.gemini_model)


settings = Settings()
