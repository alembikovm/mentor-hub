from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./mentor_hub.db"
    upload_dir: Path = Path("./uploads")
    max_upload_mb: int = 10

    # Clerk: JWKS endpoint of your Clerk instance, e.g.
    # https://<your-app>.clerk.accounts.dev/.well-known/jwks.json
    clerk_jwks_url: str = ""
    # Optional: expected `iss` claim (your Clerk Frontend API URL).
    clerk_issuer: str | None = None
    # Comma-separated list of allowed `azp` origins (e.g. http://localhost:3000).
    clerk_authorized_parties: str = "http://localhost:3000"

    cors_origins: str = "http://localhost:3000"

    # Vision analysis (Claude). Key from ANTHROPIC_API_KEY in .env or the environment.
    anthropic_api_key: str | None = None
    analysis_model: str = "claude-haiku-5-5"
    analysis_effort: str = "high"

    @property
    def authorized_parties(self) -> list[str]:
        return [p.strip() for p in self.clerk_authorized_parties.split(",") if p.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
