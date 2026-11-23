"""Tests for the FastMCP Forensics Lab server and forensic algorithms."""

from __future__ import annotations

import asyncio

from mystery_engine.cases import CURATED_CASES
from mystery_engine.mcp_server.forensics_server import (
    create_mcp_server,
    run_alibi_verification,
    run_cipher_decode,
    run_fingerprint_analysis,
)


def test_fingerprint_analysis_known_and_unknown():
    hit = run_fingerprint_analysis("fp-sterling-209")
    assert hit["status"] == "success"
    assert hit["owner"] == "Marcus Sterling"

    miss = run_fingerprint_analysis("FP-UNKNOWN-000")
    assert miss["status"] == "not_found"


def test_alibi_timeline_verification():
    contradicted = run_alibi_verification("Marcus Sterling", "21:20-21:40")
    assert contradicted["status"] == "success"
    assert contradicted["verified"] is False

    confirmed = run_alibi_verification("Clara Vance", "21:15-21:45")
    assert confirmed["status"] == "success"
    assert confirmed["verified"] is True

    missing = run_alibi_verification("Unknown Guest", "21:00-22:00")
    assert missing["status"] == "not_found"


def test_cipher_decode_matches_both_curated_cases():
    noir_clue = next(c for c in CURATED_CASES["noir"].clues if c.cipher_text)
    noir_decoded = run_cipher_decode(noir_clue.cipher_text or "", shift=3)
    assert noir_decoded["decoded_text"] == "MEET AT DOCK FOUR WITH CHRONOMETER"

    scifi_clue = next(c for c in CURATED_CASES["scifi"].clues if c.cipher_text)
    scifi_decoded = run_cipher_decode(scifi_clue.cipher_text or "", shift=3)
    assert scifi_decoded["decoded_text"] == "DIVERT HELION TO SECTOR NINE"


def test_mcp_server_registers_and_executes_forensics_tools():
    mcp = create_mcp_server()
    tools = asyncio.run(mcp.list_tools())
    tool_names = {tool.name for tool in tools}
    assert tool_names == {
        "analyze_fingerprint",
        "verify_alibi_timeline",
        "decode_cipher_note",
    }

    result = asyncio.run(
        mcp.call_tool("decode_cipher_note", {"cipher_text": "PHHW DW GRFN IRXU", "shift": 3})
    )
    assert "MEET AT DOCK FOUR" in str(result)
