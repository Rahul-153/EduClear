"""Runtime settings. Secrets come from .env only (never logged)."""
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    database_url: str = f"sqlite:///{ROOT / 'educlear.db'}"
    data_dir: Path = ROOT / "data" / "colleges"
    zapier_webhook_url: str = ""
    paypal_env: str = "sandbox"  # only value ever accepted (NFR-05); enforced in Phase 5
    inr_to_usd_rate: float = 0.0120  # D-08, fixed and shown in UI
    paypal_client_id: str = ""
    paypal_client_secret: str = ""
    paypal_webhook_id: str = ""
    paypal_counsellor_payout_email: str = ""
    channel3_api_key: str = ""
    paypal_mcp_enabled: bool = True  # agent orders go through the PayPal MCP server when available; false = direct REST only
    llm_provider: str = "auto"  # auto | ollama | openrouter | together | dashscope | hf
    llm_api_key: str = ""
    llm_model: str = ""
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:4b"
    # Accounts (PLAN_AUTH.md). Guests keep working: checkout stays open to them until GUEST_CHECKOUT=false.
    env: str = "development"  # "production" turns off demo helpers and requires a real mailer
    auth_secret: str = ""  # keys the code hashes; set in production (unset = a per-process secret, fine for dev)
    guest_checkout: bool = True
    auth_show_code: bool = False  # demo only: return the sign-in code in the response so a judge can log in without email
    llm_local_fallback: bool = True  # when a hosted model fails or is rate-limited, try local Ollama if it is running
    llm_phrasing: bool = False  # optional LLM re-phrasing of finished answers (slower; numbers are guarded either way)

    @field_validator("database_url")
    @classmethod
    def _driver(cls, v: str) -> str:
        """Render hands out postgres:// or postgresql:// URLs; SQLAlchemy needs the psycopg3 driver name."""
        for prefix in ("postgres://", "postgresql://"):
            if v.startswith(prefix):
                return "postgresql+psycopg://" + v[len(prefix):]
        return v


settings = Settings()
