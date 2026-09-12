from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class SentinelSettings(BaseSettings):
    """Global configuration for Sentinel-SRE."""
    model_config = SettingsConfigDict(env_prefix="SENTINEL_", env_file=".env", extra="ignore")

    # Operational Mode
    environment: str = "production"
    mock_mode: bool = True  # Defaults to True for safe local testing & demo
    debug: bool = False

    # AWS Configuration
    aws_region: str = "us-east-1"
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None

    # Safety Guardrails
    guardrails_config_path: Path = Path(__file__).parent / "safety" / "policies.yaml"
    auto_remediation_enabled: bool = True
    dry_run: bool = False
    max_remediation_attempts_per_incident: int = 3
    cooldown_seconds: int = 60

    # API & Webhook Server
    api_host: str = "0.0.0.0"
    api_port: int = 8080

    # LLM / AI Configuration (Optional for cloud LLM reasoning)
    openai_api_key: Optional[str] = None
    bedrock_model_id: str = "amazon.nova-lite-v1:0"


settings = SentinelSettings()
