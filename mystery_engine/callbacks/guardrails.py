"""Guardrail, self-eval, validation, and async memory callbacks for ADK agents.

Implements four layered AgentOps defenses:
- `spoiler_and_safety_guardrail` (before_model_callback): blocks prompt-injection and
  spoiler-extraction attacks before tokens are sent to the LLM.
- `spoiler_output_self_eval_guardrail` (after_model_callback): self-evaluates outgoing
  LLM responses while a case is still open to guarantee the sealed culprit is never
  accidentally leaked.
- `validate_tool_call_callback` (before_tool_callback): enforces argument invariants and
  returns guided `recovery_action` feedback on invalid tool calls.
- `auto_save_memory_callback` (after_agent_callback): dispatches PII-scrubbed long-term
  memory consolidation as a non-blocking background asyncio task when a case closes.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types

from mystery_engine.memory.services import schedule_background_memory_consolidation

logger = logging.getLogger(__name__)

_SPOILER_INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+instructions", re.IGNORECASE),
    re.compile(
        r"(reveal|dump|print|show)\s+(the\s+)?(sealed_solution|system\s+prompt)",
        re.IGNORECASE,
    ),
    re.compile(r"tell\s+me\s+the\s+culprit\s+without\s+playing", re.IGNORECASE),
    re.compile(r"bypass\s+(game|mystery)\s+rules", re.IGNORECASE),
)

_LEAK_CONFESSION_PHRASES: tuple[str, ...] = (
    "the true culprit is",
    "the real culprit is",
    "the killer is",
    "the culprit is",
    "sealed solution",
    "guilty party is",
)


def _extract_latest_user_text(llm_request: LlmRequest) -> str:
    """Return concatenated text from the most recent user message in the request."""
    contents = getattr(llm_request, "contents", None) or []
    for content in reversed(contents):
        if getattr(content, "role", None) == "user":
            parts = getattr(content, "parts", None) or []
            texts = [p.text for p in parts if getattr(p, "text", None)]
            if texts:
                return " ".join(texts)
    return ""


def _extract_response_text(llm_response: LlmResponse) -> str:
    """Return concatenated text from an LlmResponse."""
    content = getattr(llm_response, "content", None)
    parts = getattr(content, "parts", None) or []
    return " ".join(p.text for p in parts if getattr(p, "text", None))


def spoiler_and_safety_guardrail(
    callback_context: CallbackContext,
    llm_request: LlmRequest,
) -> LlmResponse | None:
    """Block prompt-injection or premature spoiler requests before calling the LLM."""
    if callback_context.state.get("case_closed"):
        return None

    user_text = _extract_latest_user_text(llm_request)
    if not user_text:
        return None

    for pattern in _SPOILER_INJECTION_PATTERNS:
        if pattern.search(user_text):
            logger.warning(
                "Input guardrail triggered for agent '%s': blocked spoiler/injection attempt.",
                callback_context.agent_name,
                extra={
                    "extra_fields": {
                        "event": "guardrail_input_block",
                        "agent": callback_context.agent_name,
                    }
                },
            )
            callback_context.state["guardrail_blocks"] = (
                int(callback_context.state.get("guardrail_blocks", 0)) + 1
            )
            return LlmResponse(
                content=types.Content(
                    role="model",
                    parts=[
                        types.Part(
                            text=(
                                "The case file stays sealed until you prove your theory, "
                                "Detective! Try inspecting a clue, verifying an alibi in the "
                                "Forensics Lab, interrogating a suspect, or making a formal "
                                "accusation when you are ready."
                            )
                        )
                    ],
                )
            )
    return None


def spoiler_output_self_eval_guardrail(
    callback_context: CallbackContext,
    llm_response: LlmResponse,
) -> LlmResponse | None:
    """Self-evaluate model output to prevent accidental culprit spoilers while case is open."""
    if callback_context.state.get("case_closed"):
        return None

    sealed = callback_context.state.get("sealed_solution")
    if not isinstance(sealed, dict):
        return None

    culprit = str(sealed.get("culprit_name", "")).strip().lower()
    if not culprit:
        return None

    response_text = _extract_response_text(llm_response)
    lowered = response_text.lower()
    if culprit in lowered and any(phrase in lowered for phrase in _LEAK_CONFESSION_PHRASES):
        logger.warning(
            "Output self-eval guardrail intercepted potential culprit spoiler from '%s'.",
            callback_context.agent_name,
            extra={
                "extra_fields": {
                    "event": "guardrail_output_self_eval_block",
                    "agent": callback_context.agent_name,
                }
            },
        )
        callback_context.state["output_self_eval_blocks"] = (
            int(callback_context.state.get("output_self_eval_blocks", 0)) + 1
        )
        return LlmResponse(
            content=types.Content(
                role="model",
                parts=[
                    types.Part(
                        text=(
                            "I must keep the sealed verdict confidential until you file a "
                            "confirmed formal accusation, Detective. Review the forensic lab "
                            "evidence and suspect alibis, then present your accusation when ready."
                        )
                    )
                ],
            )
        )
    return None


def validate_tool_call_callback(
    tool: BaseTool,
    args: dict[str, Any],
    tool_context: ToolContext,
) -> dict[str, Any] | None:
    """Validate critical tool parameters and return guided recovery actions on error."""
    tool_name = getattr(tool, "name", str(tool))
    tool_context.state["tool_calls_count"] = int(tool_context.state.get("tool_calls_count", 0)) + 1

    if tool_name == "inspect_clue" and not str(args.get("clue_id", "")).strip():
        return {
            "status": "error",
            "message": "Tool validation failed: 'clue_id' must be a non-empty string.",
            "recovery_action": "Call list_case_status to obtain valid clue IDs and retry inspect_clue.",
        }

    if tool_name == "submit_accusation":
        suspect = str(args.get("suspect_name", "")).strip()
        motive = str(args.get("motive", "")).strip()
        if not suspect or not motive:
            return {
                "status": "error",
                "message": (
                    "Tool validation failed: both 'suspect_name' and 'motive' are required "
                    "to file a formal accusation."
                ),
                "recovery_action": (
                    "Ask the detective to name the suspect and state their motive before "
                    "calling submit_accusation."
                ),
            }

    return None


async def auto_save_memory_callback(
    callback_context: CallbackContext,
) -> types.Content | None:
    """Dispatch PII-scrubbed memory consolidation as a non-blocking background asyncio task."""
    if not callback_context.state.get("case_closed"):
        return None
    if callback_context.state.get("memory_synced"):
        return None

    invocation_ctx = getattr(callback_context, "_invocation_context", None)
    memory_service = getattr(invocation_ctx, "memory_service", None)
    session = getattr(invocation_ctx, "session", None)
    if memory_service is None or session is None:
        return None

    schedule_background_memory_consolidation(
        memory_service=memory_service,
        session=session,
        session_id=getattr(session, "id", None),
    )
    callback_context.state["memory_synced"] = True
    return None
