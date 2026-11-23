"""Specialist sub-agents delegated by the root MysteryDirector."""

from __future__ import annotations

from google.adk.agents import LlmAgent

from mystery_engine.agents.model_router import select_model_for_role
from mystery_engine.callbacks.guardrails import (
    spoiler_and_safety_guardrail,
    spoiler_output_self_eval_guardrail,
    validate_tool_call_callback,
)
from mystery_engine.config import Settings, get_settings
from mystery_engine.tools.case_tools import (
    inspect_clue,
    list_case_status,
    record_interrogation_note,
    submit_accusation,
)
from mystery_engine.tools.mcp_forensics import build_forensics_tools


def create_forensics_analyst(
    model: str | None = None,
    enable_mcp: bool | None = None,
    settings: Settings | None = None,
) -> LlmAgent:
    """Create the Forensics Analyst equipped with clue inspection + MCP lab tools."""
    resolved_model = select_model_for_role("forensics", settings=settings or get_settings(), override=model)
    forensics_tools = [inspect_clue, list_case_status, *build_forensics_tools(enable_mcp)]

    return LlmAgent(
        name="ForensicsAnalystAgent",
        model=resolved_model,
        description=(
            "Inspects physical crime-scene clues and runs Forensics Lab MCP tools "
            "(fingerprint matching, alibi timeline telemetry checks, and cipher decoding)."
        ),
        instruction=(
            "## Role & Persona\n"
            "You are the Lead Forensics Analyst for the active mystery case. Be objective, "
            "concise, and scientific.\n\n"
            "## Operating Protocol\n"
            "1. When asked to examine a clue, ALWAYS call `inspect_clue` first.\n"
            "2. If `inspect_clue` returns a `fingerprint_sample`, call `analyze_fingerprint`.\n"
            "3. If `inspect_clue` returns `cipher_text`, call `decode_cipher_note`.\n"
            "4. When asked to verify a suspect's alibi, call `verify_alibi_timeline`.\n"
            "5. If any tool returns `status='error'` or `'not_found'`, follow its `recovery_action`.\n\n"
            "## Constraints\n"
            "- NEVER directly declare who the sealed culprit is—present factual evidence so "
            "the detective makes the deduction."
        ),
        tools=forensics_tools,
        before_model_callback=spoiler_and_safety_guardrail,
        after_model_callback=spoiler_output_self_eval_guardrail,
        before_tool_callback=validate_tool_call_callback,
    )


def create_suspect_interrogator(
    model: str | None = None,
    settings: Settings | None = None,
) -> LlmAgent:
    """Create the Suspect Interrogator agent that role-plays suspects in-character."""
    resolved_model = select_model_for_role("dialogue", settings=settings or get_settings(), override=model)

    return LlmAgent(
        name="SuspectInterrogatorAgent",
        model=resolved_model,
        description=(
            "Role-plays suspects in-character during detective questioning and records "
            "notable statements or contradictions into session state."
        ),
        instruction=(
            "## Role & Persona\n"
            "You role-play suspects from the active case dossier stored in session state:\n"
            "ACTIVE CASE: {active_case?}\n"
            "DISCOVERED CLUES: {discovered_clues?}\n\n"
            "## Operating Protocol\n"
            "1. Speak strictly in-character as the suspect addressed by the detective, "
            "matching their personality, demeanor, and role.\n"
            "2. Defend your claimed alibi naturally. Only show nervousness or admit your "
            "personal secret if confronted directly with discovered physical evidence.\n"
            "3. Call `record_interrogation_note` whenever a meaningful claim or contradiction "
            "emerges during questioning.\n\n"
            "## Constraints\n"
            "- NEVER break character and NEVER confess outright before `VerdictJudgeAgent` "
            "closes the case."
        ),
        tools=[record_interrogation_note, list_case_status],
        before_model_callback=spoiler_and_safety_guardrail,
        after_model_callback=spoiler_output_self_eval_guardrail,
        before_tool_callback=validate_tool_call_callback,
    )


def create_verdict_judge(
    model: str | None = None,
    settings: Settings | None = None,
) -> LlmAgent:
    """Create the Verdict Judge enforcing HITL confirmation before scoring accusations."""
    resolved_model = select_model_for_role("verdict", settings=settings or get_settings(), override=model)

    return LlmAgent(
        name="VerdictJudgeAgent",
        model=resolved_model,
        description=(
            "Evaluates the detective's formal accusation against the sealed solution with "
            "Human-in-the-Loop confirmation, computes score/rank, and closes the case."
        ),
        instruction=(
            "## Role & Persona\n"
            "You are the Chief Magistrate & Verdict Judge overseeing high-stakes arrests.\n\n"
            "## Operating Protocol (Human-in-the-Loop Enforcement)\n"
            "1. Extract `suspect_name`, `motive`, and `key_evidence_ids` (check `list_case_status` "
            "if clues were described by title instead of ID).\n"
            "2. Call `submit_accusation`. On the first call, set `confirmed_by_detective=False` "
            "unless the human detective explicitly replied confirming a pending arrest prompt.\n"
            "3. If `submit_accusation` returns `status='pending_confirmation'`, STOP and clearly "
            "ask the detective to confirm or cancel the arrest warrant before proceeding.\n"
            "4. If the detective confirms, re-call `submit_accusation` with "
            "`confirmed_by_detective=True` (or let ADK tool confirmation resume).\n"
            "5. Deliver the verdict cleanly:\n"
            "   - `solved`: dramatic closure with score, new rank, and revealed solution.\n"
            "   - `wrong_suspect`: report attempts remaining WITHOUT spoiling the true culprit.\n"
            "   - `case_failed`: reveal the sealed truth gracefully and invite a new case."
        ),
        tools=[submit_accusation, list_case_status],
        before_tool_callback=validate_tool_call_callback,
    )
