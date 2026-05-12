"""
Application configuration loaded from environment variables.
Uses pydantic-settings for validation and type coercion.
"""

from __future__ import annotations

from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    # ── Project ──
    PROJECT_NAME: str = "DeSci Compute Network"
    VERSION: str = "2.0.0"
    API_PREFIX: str = "/api/v1"

    # ── Supabase PostgreSQL ──
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/desci_compute"
    SYNC_DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/desci_compute"

    @property
    def asyncpg_url(self) -> str:
        """Append PgBouncer cache disable flags to the URL."""
        url = self.DATABASE_URL
        if "6543" in url and "prepared_statement_cache_size=0" not in url:
            sep = "&" if "?" in url else "?"
            url += f"{sep}prepared_statement_cache_size=0&statement_cache_size=0"
        return url

    # ── Supabase Storage ──
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    SUPABASE_STORAGE_BUCKET: str = "desci-compute"

    # ── Redis ──
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Auth / JWT ──
    SECRET_KEY: str = "change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # ── Torque Protocol ──
    TORQUE_API_KEY: str = ""
    TORQUE_API_URL: str = "https://api.torque.so"

    # ── OpenRouter (GPT-4o for MCP strategic decisions) ──
    OPENROUTER_API_KEY: str = ""

    # ── CORS ──
    CORS_ORIGINS: str = "*"

    # ── Task System ──
    TASK_LOCK_TIMEOUT_SECONDS: int = 300
    HEARTBEAT_INTERVAL_SECONDS: int = 30
    HEARTBEAT_TIMEOUT_SECONDS: int = 90
    STALE_TASK_CHECK_INTERVAL_SECONDS: int = 60
    MAX_TASK_RETRIES: int = 5
    VALIDATION_DUPLICATE_COUNT: int = 2
    SPOT_CHECK_PROBABILITY: float = 0.1

    # ── MCP Engine ──
    MCP_CHECK_INTERVAL_SECONDS: int = 30
    WORKER_SHORTAGE_MULTIPLIER: float = 1.5
    INACTIVITY_THRESHOLD_HOURS: int = 24

    # ── Treasury & Budget ──
    TREASURY_INITIAL_BALANCE: float = 100_000.0
    TREASURY_EMERGENCY_RESERVE: float = 10_000.0
    MAX_CAMPAIGN_BUDGET_PERCENTAGE: float = 0.15
    MAX_ACTIVE_CAMPAIGNS: int = 8
    CAMPAIGN_ORCHESTRATION_INTERVAL_CYCLES: int = 3

    # ── Solana ──
    SOLANA_RPC_URL: str = "https://api.devnet.solana.com"
    SOLANA_NETWORK: str = "devnet"
    TREASURY_WALLET_ADDRESS: str = ""
    TREASURY_PRIVATE_KEY: str = ""
    TREASURY_KEYPAIR_PATH: str = ""

    # ── Dataset ──
    MAX_DATASET_SIZE_MB: int = 100
    DATASET_CHUNK_SIZE: int = 10000

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
