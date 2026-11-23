"""Tests for OpenTelemetry spans, PII redaction, JSON logs, and Intent-vs-Outcome plugin."""

from __future__ import annotations

import json
import logging
from types import SimpleNamespace

from mystery_engine.config import Settings
from mystery_engine.observability.logging_config import JsonLogFormatter
from mystery_engine.observability.pii_redaction import redact_pii, redact_structure
from mystery_engine.observability.plugin import MysteryObservabilityPlugin
from mystery_engine.observability.telemetry import configure_telemetry, get_tracer


def test_pii_redaction_scrubs_sensitive_values_and_preserves_game_ids():
    fake_key = "AIza" + "SyTestPlaceholderKey1234567890abcd"
    raw = (
        f"Email alice@example.com phone 415-555-0199 SSN 123-45-6789 "
        f"key {fake_key} sample FP-STERLING-209"
    )
    scrubbed = redact_pii(raw, use_cloud_dlp=False)
    assert "alice@example.com" not in scrubbed
    assert "415-555-0199" not in scrubbed
    assert "123-45-6789" not in scrubbed
    assert fake_key not in scrubbed
    assert "[REDACTED_EMAIL]" in scrubbed
    assert "[REDACTED_PHONE]" in scrubbed
    assert "[REDACTED_SSN]" in scrubbed
    assert "[REDACTED_API_KEY]" in scrubbed
    assert "FP-STERLING-209" in scrubbed

    nested = redact_structure({"api_key": "secret123", "note": "Reach bob@test.io"})
    assert nested["api_key"] == "[REDACTED_SECRET]"
    assert nested["note"] == "Reach [REDACTED_EMAIL]"


def test_json_log_formatter_correlates_otel_trace_and_scrubs_pii():
    configure_telemetry(Settings(otel_exporter="none"), force=True)
    tracer = get_tracer("test.observability")
    formatter = JsonLogFormatter()

    with tracer.start_as_current_span("test-case-span"):
        record = logging.LogRecord(
            name="mystery.test",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="Clue analyzed for user@example.com",
            args=(),
            exc_info=None,
        )
        record.extra_fields = {"clue_id": "clue_1", "email": "user@example.com"}
        parsed = json.loads(formatter.format(record))

    assert parsed["level"] == "INFO"
    assert "[REDACTED_EMAIL]" in parsed["message"]
    assert parsed["email"] == "[REDACTED_EMAIL]"
    assert parsed["clue_id"] == "clue_1"
    assert len(parsed["trace_id"]) == 32
    assert len(parsed["span_id"]) == 16


async def test_observability_plugin_captures_intent_vs_outcome_and_metrics(
    tool_context, callback_context
):
    plugin = MysteryObservabilityPlugin()
    agent = SimpleNamespace(name="MysteryDirector")
    tool = SimpleNamespace(name="inspect_clue")
    llm_response = SimpleNamespace(
        usage_metadata=SimpleNamespace(prompt_token_count=120, candidates_token_count=45)
    )

    await plugin.before_agent_callback(agent=agent, callback_context=callback_context)
    await plugin.before_model_callback(
        callback_context=callback_context, llm_request=SimpleNamespace()
    )
    await plugin.after_model_callback(callback_context=callback_context, llm_response=llm_response)
    await plugin.before_tool_callback(
        tool=tool,
        tool_args={"clue_id": "clue_1", "note": "owner@example.com"},
        tool_context=tool_context,
    )
    await plugin.after_tool_callback(
        tool=tool,
        tool_args={"clue_id": "clue_1"},
        tool_context=tool_context,
        result={"status": "success"},
    )
    await plugin.before_tool_callback(
        tool=tool,
        tool_args={"clue_id": "bad"},
        tool_context=tool_context,
    )
    await plugin.on_tool_error_callback(
        tool=tool,
        tool_args={"clue_id": "bad"},
        tool_context=tool_context,
        error=RuntimeError("lab offline for user@example.com"),
    )
    await plugin.after_agent_callback(agent=agent, callback_context=callback_context)

    snapshot = plugin.snapshot_metrics()
    assert snapshot["agent_invocations"]["MysteryDirector"] == 1
    assert snapshot["llm_calls"] == 1
    assert snapshot["prompt_tokens"] == 120
    assert snapshot["candidate_tokens"] == 45
    assert snapshot["tool_calls"]["inspect_clue"] == 2
    assert snapshot["tool_errors"]["inspect_clue"] == 1
    assert "inspect_clue" in snapshot["avg_tool_latency_ms"]

    records = snapshot["recent_intent_vs_outcome"]
    assert len(records) == 2
    assert records[0]["intended_tool"] == "inspect_clue"
    assert records[0]["intended_args"]["note"] == "[REDACTED_EMAIL]"
    assert records[0]["outcome_status"] == "success"
    assert records[0]["intent_succeeded"] is True
    assert records[1]["outcome_status"] == "exception"
    assert records[1]["intent_succeeded"] is False
    assert "[REDACTED_EMAIL]" in records[1]["error_message"]
