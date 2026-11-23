"""ADK McpToolset wiring for the local Forensics Lab MCP server."""

from __future__ import annotations

import logging
import sys
from typing import Any

from mystery_engine.config import get_settings
from mystery_engine.mcp_server.forensics_server import (
    run_alibi_verification,
    run_cipher_decode,
    run_fingerprint_analysis,
)

logger = logging.getLogger(__name__)


def analyze_fingerprint_local(sample_id: str) -> dict[str, Any]:
    """Match a crime-scene fingerprint sample ID against the local forensics lab registry.

    Args:
        sample_id: Fingerprint token discovered during clue inspection (e.g. 'FP-STERLING-209').

    Returns:
        Structured lab report with owner match, confidence score, and residue notes.
    """
    return run_fingerprint_analysis(sample_id)


def verify_alibi_timeline_local(suspect_name: str, claimed_window: str) -> dict[str, Any]:
    """Verify a suspect's claimed alibi window against independent facility telemetry logs.

    Args:
        suspect_name: Full name of the suspect being checked.
        claimed_window: Time range claimed by the suspect (e.g. '21:20-21:40').

    Returns:
        Structured verification report indicating whether telemetry corroborates the alibi.
    """
    return run_alibi_verification(suspect_name, claimed_window)


def decode_cipher_note_local(cipher_text: str, shift: int = 3) -> dict[str, Any]:
    """Decrypt an intercepted Caesar-ciphered clue note.

    Args:
        cipher_text: Encoded message string extracted from a physical clue.
        shift: Caesar letter rotation offset (defaults to 3).

    Returns:
        Structured dictionary containing the plaintext `decoded_text`.
    """
    return run_cipher_decode(cipher_text, shift)


def create_forensics_mcp_toolset() -> Any:
    """Build an ADK McpToolset talking to forensics_server.py over stdio."""
    from google.adk.tools.mcp_tool import McpToolset
    from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
    from mcp import StdioServerParameters

    return McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command=sys.executable,
                args=["-m", "mystery_engine.mcp_server.forensics_server"],
            ),
            timeout=15.0,
        ),
        tool_filter=[
            "analyze_fingerprint",
            "verify_alibi_timeline",
            "decode_cipher_note",
        ],
    )


def build_forensics_tools(enable_mcp: bool | None = None) -> list[Any]:
    """Return MCP toolset when enabled, or typed local fallbacks for offline tests."""
    use_mcp = get_settings().enable_mcp_forensics if enable_mcp is None else enable_mcp
    if use_mcp:
        try:
            return [create_forensics_mcp_toolset()]
        except Exception as exc:  # pragma: no cover - defensive fallback
            logger.warning(
                "Falling back to local forensics tools because McpToolset init failed: %s",
                exc,
            )
    return [
        analyze_fingerprint_local,
        verify_alibi_timeline_local,
        decode_cipher_note_local,
    ]
