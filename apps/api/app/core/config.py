from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    env: Literal["local", "test", "production"] = "local"
    app_name: str = "Móyee API"

    # Database: defaults to local SQLite in dev so it runs with zero setup;
    # set to your Supabase Postgres URI in production.
    database_url: str = "sqlite:///./moyee_local.db"

    # Supabase auth
    supabase_url: str = ""
    # Legacy HS256 JWT secret. Leave empty when using asymmetric signing keys (JWKS).
    supabase_jwt_secret: str = ""
    supabase_jwt_audience: str = "authenticated"

    # CORS
    web_origin: str = "http://localhost:3000"

    # OpenAlex polite pool contact
    openalex_mailto: str = ""

    # Local storage directory for uploaded PDFs (used when S3/Supabase storage is not configured)
    storage_dir: str = ".storage"

    # AI providers (provider-agnostic gateway)
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    # Paystack billing (test mode by default)
    paystack_secret_key: str = "sk_test_moyee_dev"
    paystack_public_key: str = ""

    @property
    def jwks_url(self) -> str:
        return f"{self.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()
