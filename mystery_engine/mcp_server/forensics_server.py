"""Standalone FastMCP Forensics Lab Server (stdio transport).

Exposes standardized Model Context Protocol (MCP) tools consumed by the
ForensicsAnalystAgent via ADK's McpToolset:
  - analyze_fingerprint: Matches a sample ID against the forensics registry.
  - verify_alibi_timeline: Cross-checks a suspect's claimed alibi against telemetry.
  - decode_cipher_note: Decrypts Caesar-shifted intercepted notes.

Run standalone:
    python -m mystery_engine.mcp_server.forensics_server
"""

from __future__ import annotations

from typing import Any

from mystery_engine.cases import ALIBI_TELEMETRY_RECORDS, FINGERPRINT_DATABASE


def run_fingerprint_analysis(sample_id: str) -> dict[str, Any]:
    """Match a forensic fingerprint sample ID against the lab database.

    Args:
        sample_id: Crime-scene fingerprint sample token (e.g. 'FP-STERLING-209').

    Returns:
        Dictionary with `status`, matched `owner`, `confidence`, and forensic `notes`,
        or `not_found` with a guided `recovery_action`.
    """
    normalized = sample_id.strip().upper()
    if not normalized:
        return {
            "status": "error",
            "message": "Fingerprint sample_id cannot be empty.",
            "recovery_action": "Call inspect_clue on a clue first to obtain its fingerprint_sample ID.",
        }
    record = FINGERPRINT_DATABASE.get(normalized)
    if record is None:
        return {
            "status": "not_found",
            "sample_id": normalized,
            "message": f"No fingerprint match in lab registry for '{normalized}'.",
            "recovery_action": (
                "Verify the exact fingerprint_sample string returned by inspect_clue, or "
                "rely on alibi timeline and cipher analysis for this custom suspect."
            ),
        }
    return {
        "status": "success",
        "sample_id": normalized,
        **record,
    }


def run_alibi_verification(suspect_name: str, claimed_window: str) -> dict[str, Any]:
    """Cross-check a suspect's claimed alibi window against station/building logs.

    Args:
        suspect_name: Full name of the suspect whose alibi should be audited.
        claimed_window: Time window claimed by the suspect (e.g. '21:20-21:40').

    Returns:
        Dictionary with `status`, boolean `verified`, telemetry `source`, and `detail`,
        or `not_found` with a guided `recovery_action`.
    """
    normalized = suspect_name.strip().lower()
    if not normalized:
        return {
            "status": "error",
            "message": "suspect_name cannot be empty.",
            "recovery_action": "Call list_case_status to get exact suspect names, then retry.",
        }
    record = ALIBI_TELEMETRY_RECORDS.get(normalized)
    if record is None:
        return {
            "status": "not_found",
            "suspect_name": suspect_name,
            "claimed_window": claimed_window,
            "message": f"No independent telemetry logs found for '{suspect_name}'.",
            "recovery_action": (
                "Check the exact suspect spelling via list_case_status or interrogate the "
                "suspect directly to probe their alibi."
            ),
        }
    return {
        "status": "success",
        "suspect_name": suspect_name,
        "claimed_window": claimed_window,
        **record,
    }


def run_cipher_decode(cipher_text: str, shift: int = 3) -> dict[str, Any]:
    """Decrypt a Caesar-cipher note by shifting alphabetic characters backward.

    Args:
        cipher_text: Encoded uppercase or lowercase message recovered from a clue.
        shift: Integer Caesar rotation offset (defaults to 3).

    Returns:
        Dictionary containing `status`, normalized `shift`, original `cipher_text`,
        and decrypted `decoded_text`.
    """
    if not cipher_text.strip():
        return {
            "status": "error",
            "message": "cipher_text cannot be empty.",
            "recovery_action": "Call inspect_clue to retrieve the exact cipher_text string first.",
        }
    normalized_shift = shift % 26
    decoded_chars: list[str] = []
    for ch in cipher_text:
        if "A" <= ch <= "Z":
            decoded_chars.append(chr((ord(ch) - ord("A") - normalized_shift) % 26 + ord("A")))
        elif "a" <= ch <= "z":
            decoded_chars.append(chr((ord(ch) - ord("a") - normalized_shift) % 26 + ord("a")))
        else:
            decoded_chars.append(ch)
    return {
        "status": "success",
        "shift": normalized_shift,
        "cipher_text": cipher_text,
        "decoded_text": "".join(decoded_chars),
    }


def create_mcp_server():
    """Instantiate the MCP server exposing the forensics lab tools (MCP 1.x & 2.x compatible)."""
    try:
        from mcp.server.mcpserver import MCPServer as ServerClass
    except ImportError:
        from mcp.server.fastmcp import FastMCP as ServerClass  # type: ignore[no-redef]

    mcp = ServerClass("mystery-forensics-lab")

    @mcp.tool()
    def analyze_fingerprint(sample_id: str) -> dict[str, Any]:
        """Match a crime-scene fingerprint sample ID (e.g. FP-STERLING-209) in the lab registry."""
        return run_fingerprint_analysis(sample_id)

    @mcp.tool()
    def verify_alibi_timeline(suspect_name: str, claimed_window: str) -> dict[str, Any]:
        """Verify a suspect's claimed alibi time window against independent telemetry logs."""
        return run_alibi_verification(suspect_name, claimed_window)

    @mcp.tool()
    def decode_cipher_note(cipher_text: str, shift: int = 3) -> dict[str, Any]:
        """Decode a Caesar-encrypted clue note using the given letter shift (default 3)."""
        return run_cipher_decode(cipher_text, shift)

    return mcp


if __name__ == "__main__":
    server = create_mcp_server()
    server.run(transport="stdio")
