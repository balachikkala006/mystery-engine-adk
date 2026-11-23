"""Typed runtime configuration for the Interactive AI Mystery Engine."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

_ROOT_ENV = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_ROOT_ENV)
load_dotenv()


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    """Centralized application settings loaded from environment variables."""

    app_name: str = "mystery_engine"
    # Strategic Model Routing tiers:
    # - fast_model: low-latency interactive routing, tool calls, dialogue, verdict
    # - planning_model: high-reasoning worldbuilding, suspect design, lore critique
    model_name: str = os.getenv("MYSTERY_MODEL", "gemini-3.5-flash")
    fast_model: str = os.getenv("MYSTERY_FAST_MODEL", os.getenv("MYSTERY_MODEL", "gemini-3.5-flash"))
    planning_model: str = os.getenv("MYSTERY_PLANNING_MODEL", "gemini-3.8-flash")
    session_backend: str = os.getenv("SESSION_BACKEND", "sqlite").lower()
    session_db_path: str = os.getenv("SESSION_DB_PATH", "data/sessions/mystery_sessions.db")
    agent_engine_id: str | None = os.getenv("AGENT_ENGINE_ID") or None
    gcp_project: str | None = os.getenv("GOOGLE_CLOUD_PROJECT") or None
    gcp_location: str = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    enable_mcp_forensics: bool = _parse_bool(os.getenv("ENABLE_MCP_FORENSICS"), default=True)
    enable_cloud_dlp: bool = _parse_bool(os.getenv("ENABLE_CLOUD_DLP"), default=False)
    use_secret_manager: bool = _parse_bool(os.getenv("USE_SECRET_MANAGER"), default=False)
    log_level: str = os.getenv("LOG_LEVEL", "INFO").upper()
    log_format: str = os.getenv("LOG_FORMAT", "json").lower()
    otel_exporter: str = os.getenv("OTEL_EXPORTER", "none").lower()
    otel_service_name: str = os.getenv("OTEL_SERVICE_NAME", "mystery-engine-adk")
    otel_otlp_endpoint: str = os.getenv(
        "OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318/v1/traces"
    )
    compaction_interval: int = int(os.getenv("COMPACTION_INTERVAL", "4"))
    compaction_overlap: int = int(os.getenv("COMPACTION_OVERLAP", "1"))
    max_accusation_attempts: int = int(os.getenv("MAX_ACCUSATION_ATTEMPTS", "2"))
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8080"))
    a2a_port: int = int(os.getenv("A2A_PORT", "8001"))

    def ensure_data_dirs(self) -> Path:
        """Create parent directories for local SQLite session storage."""
        db_path = Path(self.session_db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return db_path


def get_settings() -> Settings:
    """Return a freshly loaded Settings object reflecting current environment."""
    default_model = os.getenv("MYSTERY_MODEL", "gemini-3.5-flash")
    return Settings(
        model_name=default_model,
        fast_model=os.getenv("MYSTERY_FAST_MODEL", default_model),
        planning_model=os.getenv("MYSTERY_PLANNING_MODEL", "gemini-3.8-flash"),
        session_backend=os.getenv("SESSION_BACKEND", "sqlite").lower(),
        session_db_path=os.getenv("SESSION_DB_PATH", "data/sessions/mystery_sessions.db"),
        agent_engine_id=os.getenv("AGENT_ENGINE_ID") or None,
        gcp_project=os.getenv("GOOGLE_CLOUD_PROJECT") or None,
        gcp_location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
        enable_mcp_forensics=_parse_bool(os.getenv("ENABLE_MCP_FORENSICS"), default=True),
        enable_cloud_dlp=_parse_bool(os.getenv("ENABLE_CLOUD_DLP"), default=False),
        use_secret_manager=_parse_bool(os.getenv("USE_SECRET_MANAGER"), default=False),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        log_format=os.getenv("LOG_FORMAT", "json").lower(),
        otel_exporter=os.getenv("OTEL_EXPORTER", "none").lower(),
        otel_service_name=os.getenv("OTEL_SERVICE_NAME", "mystery-engine-adk"),
        otel_otlp_endpoint=os.getenv(
            "OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318/v1/traces"
        ),
        compaction_interval=int(os.getenv("COMPACTION_INTERVAL", "4")),
        compaction_overlap=int(os.getenv("COMPACTION_OVERLAP", "1")),
        max_accusation_attempts=int(os.getenv("MAX_ACCUSATION_ATTEMPTS", "2")),
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8080")),
        a2a_port=int(os.getenv("A2A_PORT", "8001")),
    )
