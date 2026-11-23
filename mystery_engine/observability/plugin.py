"""Custom ADK BasePlugin capturing distributed spans, PII-scrubbed intent vs. outcome logs, and metrics."""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.plugins.base_plugin import BasePlugin
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from mystery_engine.observability.pii_redaction import redact_pii, redact_structure
from mystery_engine.observability.telemetry import get_tracer

logger = logging.getLogger(__name__)


@dataclass
class EngineMetrics:
    """In-memory telemetry counters, latencies, and Intent-vs-Outcome audit entries."""

    agent_invocations: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    llm_calls: int = 0
    prompt_tokens: int = 0
    candidate_tokens: int = 0
    tool_calls: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    tool_errors: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    tool_latency_ms: dict[str, list[float]] = field(default_factory=lambda: defaultdict(list))
    intent_vs_outcome_records: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        avg_latency = {
            name: round(sum(samples) / len(samples), 2)
            for name, samples in self.tool_latency_ms.items()
            if samples
        }
        return {
            "agent_invocations": dict(self.agent_invocations),
            "llm_calls": self.llm_calls,
            "prompt_tokens": self.prompt_tokens,
            "candidate_tokens": self.candidate_tokens,
            "tool_calls": dict(self.tool_calls),
            "tool_errors": dict(self.tool_errors),
            "avg_tool_latency_ms": avg_latency,
            "recent_intent_vs_outcome": self.intent_vs_outcome_records[-10:],
        }


class MysteryObservabilityPlugin(BasePlugin):
    """ADK Plugin recording distributed OTel spans, Intent-vs-Outcome logs, and runtime metrics."""

    def __init__(self, name: str = "mystery_observability") -> None:
        super().__init__(name=name)
        self.metrics = EngineMetrics()
        self._tool_timers: dict[str, float] = {}
        self._tool_intents: dict[str, dict[str, Any]] = {}
        self._tool_spans: dict[str, Any] = {}
        self._agent_spans: dict[str, Any] = {}
        self._tracer = get_tracer("mystery_engine.plugin")

    def snapshot_metrics(self) -> dict[str, Any]:
        """Return a JSON-serializable snapshot of collected observability metrics."""
        return self.metrics.to_dict()

    async def before_agent_callback(
        self,
        *,
        agent: BaseAgent,
        callback_context: CallbackContext,
    ) -> Any | None:
        self.metrics.agent_invocations[agent.name] += 1
        span_key = f"{id(callback_context)}:{agent.name}"
        span = self._tracer.start_span(f"agent.run.{agent.name}")
        span.set_attribute("mystery.agent.name", agent.name)
        self._agent_spans[span_key] = span

        logger.info(
            "Agent intent: delegating turn to %s",
            agent.name,
            extra={
                "extra_fields": {
                    "event": "agent_intent",
                    "agent": agent.name,
                    "phase": "before_agent",
                }
            },
        )
        return None

    async def after_agent_callback(
        self,
        *,
        agent: BaseAgent,
        callback_context: CallbackContext,
    ) -> Any | None:
        span_key = f"{id(callback_context)}:{agent.name}"
        span = self._agent_spans.pop(span_key, None)
        if span is not None:
            span.set_status(Status(StatusCode.OK))
            span.end()

        logger.info(
            "Agent outcome: %s completed turn",
            agent.name,
            extra={
                "extra_fields": {
                    "event": "agent_outcome",
                    "agent": agent.name,
                    "phase": "after_agent",
                    "case_closed": bool(callback_context.state.get("case_closed", False)),
                }
            },
        )
        return None

    async def before_model_callback(
        self,
        *,
        callback_context: CallbackContext,
        llm_request: LlmRequest,
    ) -> LlmResponse | None:
        self.metrics.llm_calls += 1
        logger.debug(
            "LLM request dispatched by %s",
            callback_context.agent_name,
            extra={
                "extra_fields": {
                    "event": "llm_request",
                    "agent": callback_context.agent_name,
                    "llm_call_index": self.metrics.llm_calls,
                }
            },
        )
        return None

    async def after_model_callback(
        self,
        *,
        callback_context: CallbackContext,
        llm_response: LlmResponse,
    ) -> LlmResponse | None:
        usage = getattr(llm_response, "usage_metadata", None)
        if usage is not None:
            self.metrics.prompt_tokens += int(getattr(usage, "prompt_token_count", 0) or 0)
            self.metrics.candidate_tokens += int(getattr(usage, "candidates_token_count", 0) or 0)
        return None

    async def before_tool_callback(
        self,
        *,
        tool: BaseTool,
        tool_args: dict[str, Any],
        tool_context: ToolContext,
    ) -> dict[str, Any] | None:
        tool_name = getattr(tool, "name", str(tool))
        call_key = f"{id(tool_context)}:{tool_name}"
        self._tool_timers[call_key] = time.perf_counter()
        self.metrics.tool_calls[tool_name] += 1

        safe_args = redact_structure(tool_args)
        intent_record = {
            "intended_tool": tool_name,
            "intended_args": safe_args,
            "agent": getattr(tool_context, "agent_name", "unknown"),
        }
        self._tool_intents[call_key] = intent_record

        parent_ctx = trace.set_span_in_context(trace.get_current_span())
        span = self._tracer.start_span(f"tool.exec.{tool_name}", context=parent_ctx)
        span.set_attribute("mystery.tool.name", tool_name)
        span.set_attribute("mystery.tool.arg_keys", ",".join(sorted(tool_args.keys())))
        self._tool_spans[call_key] = span

        logger.info(
            "Tool intent recorded: %s",
            tool_name,
            extra={"extra_fields": {"event": "tool_intent", **intent_record}},
        )
        return None

    async def after_tool_callback(
        self,
        *,
        tool: BaseTool,
        tool_args: dict[str, Any],
        tool_context: ToolContext,
        result: dict[str, Any],
    ) -> dict[str, Any] | None:
        tool_name = getattr(tool, "name", str(tool))
        call_key = f"{id(tool_context)}:{tool_name}"
        started_at = self._tool_timers.pop(call_key, None)
        elapsed_ms = round((time.perf_counter() - started_at) * 1000.0, 2) if started_at else 0.0
        self.metrics.tool_latency_ms[tool_name].append(elapsed_ms)

        intent = self._tool_intents.pop(
            call_key,
            {"intended_tool": tool_name, "intended_args": redact_structure(tool_args)},
        )
        outcome_status = result.get("status", "success") if isinstance(result, dict) else "success"
        intent_succeeded = outcome_status in {"success", "pending_confirmation"}
        record = {
            "event": "tool_intent_vs_outcome",
            "intended_tool": intent["intended_tool"],
            "intended_args": intent["intended_args"],
            "outcome_status": str(outcome_status),
            "intent_succeeded": intent_succeeded,
            "latency_ms": elapsed_ms,
        }
        self.metrics.intent_vs_outcome_records.append(record)

        span = self._tool_spans.pop(call_key, None)
        if span is not None:
            span.set_attribute("mystery.tool.latency_ms", elapsed_ms)
            span.set_attribute("mystery.tool.outcome_status", str(outcome_status))
            span.set_attribute("mystery.tool.intent_succeeded", intent_succeeded)
            span.set_status(Status(StatusCode.OK if intent_succeeded else StatusCode.ERROR))
            span.end()

        logger.info(
            "Tool outcome recorded: %s -> %s (%.2f ms)",
            tool_name,
            outcome_status,
            elapsed_ms,
            extra={"extra_fields": record},
        )
        return None

    async def on_tool_error_callback(
        self,
        *,
        tool: BaseTool,
        tool_args: dict[str, Any],
        tool_context: ToolContext,
        error: Exception,
    ) -> dict[str, Any] | None:
        tool_name = getattr(tool, "name", str(tool))
        call_key = f"{id(tool_context)}:{tool_name}"
        started_at = self._tool_timers.pop(call_key, None)
        elapsed_ms = round((time.perf_counter() - started_at) * 1000.0, 2) if started_at else 0.0
        self.metrics.tool_errors[tool_name] += 1

        intent = self._tool_intents.pop(
            call_key,
            {"intended_tool": tool_name, "intended_args": redact_structure(tool_args)},
        )
        safe_error = redact_pii(str(error))
        record = {
            "event": "tool_intent_vs_outcome",
            "intended_tool": intent["intended_tool"],
            "intended_args": intent["intended_args"],
            "outcome_status": "exception",
            "intent_succeeded": False,
            "error_type": type(error).__name__,
            "error_message": safe_error,
            "latency_ms": elapsed_ms,
        }
        self.metrics.intent_vs_outcome_records.append(record)

        span = self._tool_spans.pop(call_key, None)
        if span is not None:
            span.record_exception(error)
            span.set_attribute("mystery.tool.outcome_status", "exception")
            span.set_status(Status(StatusCode.ERROR, safe_error))
            span.end()

        logger.error(
            "Tool error in %s: %s",
            tool_name,
            safe_error,
            extra={"extra_fields": record},
        )
        return None
