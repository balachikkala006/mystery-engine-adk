"""Shared fixtures and lightweight ADK context stubs for offline unit tests."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import pytest

# Keep test runs isolated, deterministic, and free of noisy exporters.
os.environ.setdefault("SESSION_BACKEND", "memory")
os.environ.setdefault("OTEL_EXPORTER", "none")
os.environ.setdefault("ENABLE_MCP_FORENSICS", "false")


@dataclass
class DummyActions:
    escalate: bool = False


@dataclass
class DummyToolConfirmation:
    confirmed: bool = True
    payload: Any = None


@dataclass
class DummyToolContext:
    """Minimal ToolContext stub supporting mutable state, actions, and HITL confirmations."""

    state: dict[str, Any] = field(default_factory=dict)
    actions: DummyActions = field(default_factory=DummyActions)
    function_call_id: str | None = "call_test_001"
    tool_confirmation: DummyToolConfirmation | None = None
    confirmation_requests: list[dict[str, Any]] = field(default_factory=list)

    def request_confirmation(
        self, *, hint: str | None = None, payload: Any | None = None
    ) -> None:
        self.confirmation_requests.append({"hint": hint, "payload": payload})


@dataclass
class DummyCallbackContext:
    """Minimal CallbackContext stub for testing guardrail and memory callbacks."""

    agent_name: str = "MysteryDirector"
    state: dict[str, Any] = field(default_factory=dict)
    _invocation_context: Any = None


@pytest.fixture
def tool_context() -> DummyToolContext:
    return DummyToolContext()


@pytest.fixture
def callback_context() -> DummyCallbackContext:
    return DummyCallbackContext()
