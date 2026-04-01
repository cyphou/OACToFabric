"""Application configuration using pydantic-settings."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration — loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- OAC connection ---
    oac_base_url: str = "https://oac-instance.analytics.ocp.oraclecloud.com"
    oac_client_id: str = ""
    oac_client_secret: str = ""
    oac_token_url: str = ""  # OAuth2 token endpoint
    oac_api_version: str = "20210901"

    # --- Azure OpenAI ---
    azure_openai_endpoint: str = ""
    azure_openai_key: str = ""
    azure_openai_deployment: str = "gpt-4"

    # --- Microsoft Fabric ---
    fabric_workspace_id: str = ""
    fabric_lakehouse_id: str = ""
    fabric_sql_endpoint: str = ""  # <workspace>.datawarehouse.fabric.microsoft.com

    # --- RPD file ---
    rpd_xml_path: str = ""  # Path to the exported RPD XML file

    # --- Operational ---
    log_level: str = "INFO"
    max_retries: int = 3
    retry_backoff_seconds: float = 2.0
    page_size: int = 100  # OAC API page size

    # --- Intelligence (Phase 70) ---
    intelligence_enabled: bool = False
    intelligence_model: str = "gpt-4.1"
    intelligence_temperature: float = 0.1
    intelligence_max_context_tokens: int = 60_000
    intelligence_default_token_budget: int = 500_000
    intelligence_cost_per_1k_tokens: float = 0.03
    intelligence_max_iterations: int = 10
    intelligence_cache_max_size: int = 10_000
    intelligence_memory_ttl_seconds: float = 0  # 0 = no expiry


# Singleton instance
settings = Settings()
