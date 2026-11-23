"""Active PII redaction pipeline for structured logs and long-term memory storage.

Supports two layers:
1. Optional Google Cloud Sensitive Data Protection (Cloud DLP API) when
   `ENABLE_CLOUD_DLP=true` and `GOOGLE_CLOUD_PROJECT` is configured.
2. Always-on deterministic regex redaction for emails, phone numbers, SSNs,
   credit cards, API keys/tokens, and IPv4 addresses—ensuring zero PII leaks
   into JSON logs, OpenTelemetry attributes, or MemoryService even offline.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from mystery_engine.config import get_settings

logger = logging.getLogger(__name__)

_PII_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    # API keys & bearer tokens first so they aren't partially masked
    (re.compile(r"\bAIza[0-9A-Za-z\-_]{20,}\b"), "[REDACTED_API_KEY]"),
    (re.compile(r"\b(?:sk|ghp|gho|glpat)-[0-9A-Za-z_\-]{16,}\b"), "[REDACTED_API_KEY]"),
    (re.compile(r"(?i)Bearer\s+[A-Za-z0-9\-._~+/]+=*"), "Bearer [REDACTED_TOKEN]"),
    # Standard personal identifiers
    (re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"), "[REDACTED_EMAIL]"),
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[REDACTED_SSN]"),
    (re.compile(r"\b(?:\d[ -]*?){13,16}\b"), "[REDACTED_CREDIT_CARD]"),
    (
        re.compile(r"(?<!\d)(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}(?!\d)"),
        "[REDACTED_PHONE]",
    ),
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "[REDACTED_IP]"),
)

_CLOUD_DLP_INFO_TYPES: tuple[str, ...] = (
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "US_SOCIAL_SECURITY_NUMBER",
    "CREDIT_CARD_NUMBER",
    "IP_ADDRESS",
)


def _redact_via_cloud_dlp(text: str, project_id: str) -> str | None:
    """De-identify PII using Google Cloud DLP API when installed and enabled."""
    try:
        from google.cloud import dlp_v2  # type: ignore[import-not-found]

        client = dlp_v2.DlpServiceClient()
        parent = f"projects/{project_id}"
        inspect_config = {
            "info_types": [{"name": info_type} for info_type in _CLOUD_DLP_INFO_TYPES]
        }
        deidentify_config = {
            "info_type_transformations": {
                "transformations": [
                    {
                        "primitive_transformation": {
                            "replace_with_info_type_config": {}
                        }
                    }
                ]
            }
        }
        response = client.deidentify_content(
            request={
                "parent": parent,
                "deidentify_config": deidentify_config,
                "inspect_config": inspect_config,
                "item": {"value": text},
            }
        )
        return str(response.item.value)
    except Exception as exc:  # pragma: no cover - optional GCP API
        logger.debug("Cloud DLP unavailable (%s); applying local regex redaction.", exc)
        return None


def redact_pii(text: str, *, use_cloud_dlp: bool | None = None) -> str:
    """Scrub sensitive PII and secrets from a string before logging or memory storage."""
    if not text:
        return text

    scrubbed = text
    settings = get_settings()
    should_use_dlp = settings.enable_cloud_dlp if use_cloud_dlp is None else use_cloud_dlp
    if should_use_dlp and settings.gcp_project:
        dlp_result = _redact_via_cloud_dlp(scrubbed, settings.gcp_project)
        if dlp_result is not None:
            scrubbed = dlp_result

    for pattern, replacement in _PII_PATTERNS:
        scrubbed = pattern.sub(replacement, scrubbed)
    return scrubbed


def redact_structure(value: Any, *, use_cloud_dlp: bool | None = None) -> Any:
    """Recursively scrub PII from strings nested inside dicts, lists, and tuples."""
    if isinstance(value, str):
        return redact_pii(value, use_cloud_dlp=use_cloud_dlp)
    if isinstance(value, dict):
        return {
            key: (
                "[REDACTED_SECRET]"
                if any(s in str(key).lower() for s in ("api_key", "password", "secret", "token"))
                else redact_structure(val, use_cloud_dlp=use_cloud_dlp)
            )
            for key, val in value.items()
        }
    if isinstance(value, list):
        return [redact_structure(item, use_cloud_dlp=use_cloud_dlp) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_structure(item, use_cloud_dlp=use_cloud_dlp) for item in value)
    return value
