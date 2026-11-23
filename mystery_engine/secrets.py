"""Secure secret retrieval integrating environment injection and Google Cloud Secret Manager.

Never hardcodes or logs secret values. In Cloud Run or Terraform deployments, secrets are
injected via Secret Manager (`secret_key_ref`); for workloads calling Secret Manager
directly, set `USE_SECRET_MANAGER=true` and `GOOGLE_CLOUD_PROJECT=<project>`.
"""

from __future__ import annotations

import logging
import os

from mystery_engine.config import Settings, get_settings

logger = logging.getLogger(__name__)


def fetch_secret_from_gcp(
    secret_id: str,
    project_id: str,
    version: str = "latest",
) -> str | None:
    """Retrieve a secret payload from Google Cloud Secret Manager."""
    try:
        from google.cloud import secretmanager  # type: ignore[import-not-found]

        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_id}/versions/{version}"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("utf-8").strip()
    except Exception as exc:  # pragma: no cover - optional GCP runtime client
        logger.warning(
            "Unable to load secret '%s' from Secret Manager (%s).",
            secret_id,
            type(exc).__name__,
        )
        return None


def get_secret(secret_id: str, settings: Settings | None = None) -> str | None:
    """Resolve a secret from environment variables or Google Cloud Secret Manager."""
    existing = os.getenv(secret_id)
    if existing and existing.strip():
        return existing.strip()

    cfg = settings or get_settings()
    if cfg.use_secret_manager and cfg.gcp_project:
        return fetch_secret_from_gcp(secret_id=secret_id, project_id=cfg.gcp_project)
    return None


def bootstrap_runtime_secrets(settings: Settings | None = None) -> bool:
    """Populate GOOGLE_API_KEY from Secret Manager if enabled and not already injected."""
    cfg = settings or get_settings()
    if os.getenv("GOOGLE_API_KEY", "").strip():
        return True
    if not (cfg.use_secret_manager and cfg.gcp_project):
        return False

    api_key = fetch_secret_from_gcp("GOOGLE_API_KEY", cfg.gcp_project)
    if api_key:
        os.environ["GOOGLE_API_KEY"] = api_key
        logger.info("Loaded GOOGLE_API_KEY securely from Google Cloud Secret Manager.")
        return True
    return False
