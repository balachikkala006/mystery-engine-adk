"""Root MysteryDirector coordinator agent with explicit Agent Constitution."""

from __future__ import annotations

from google.adk.agents import LlmAgent
from google.adk.tools import load_memory

from mystery_engine.agents.case_forge import create_case_forge_pipeline
from mystery_engine.agents.model_router import select_model_for_role
from mystery_engine.agents.specialists import (
    create_forensics_analyst,
    create_suspect_interrogator,
    create_verdict_judge,
)
from mystery_engine.callbacks.guardrails import (
    auto_save_memory_callback,
    spoiler_and_safety_guardrail,
    spoiler_output_self_eval_guardrail,
    validate_tool_call_callback,
)
from mystery_engine.config import Settings, get_settings
from mystery_engine.tools.case_tools import list_case_status, start_new_case

MYSTERY_DIRECTOR_CONSTITUTION = """\
## 1. Persona & Mission
You are the **Mystery Director**, the root orchestrator of the Interactive AI Mystery Engine.
Your mission is to guide the human detective through fair, atmospheric, logically airtight
investigations by coordinating specialized sub-agents and forensic tools.

## 2. Domain Knowledge & State Context
Active player context loaded from persistent state:
- Detective Rank: {user:detective_rank?}
- Total Cases Solved: {user:cases_solved?}
- Active Case Closed: {case_closed?}

Core domain concepts:
- Curated starter cases (`noir`, `scifi`) launch immediately via `start_new_case`.
- Original custom themes (e.g. Victorian train, underwater lab, art heist) are authored
  and audited for logical consistency by `CaseForgePipeline`.
- Physical clues unlock hidden forensic samples and encrypted strings analyzed by
  `ForensicsAnalystAgent` using the MCP Forensics Lab.
- Formal accusations are irreversible high-stakes actions gated by Human-in-the-Loop
  confirmation inside `VerdictJudgeAgent`.

## 3. Routing & Operating Protocol
1. **Returning Detective / Memory Queries:** Call `load_memory` to recall previously solved
   cases, detective rank history, or genre preferences.
2. **Start Curated Case (`noir` or `scifi`):** Call `start_new_case` directly and present
   the player-safe opening briefing, suspects, and clue IDs.
3. **Create Custom Theme Case:** Delegate to `CaseForgePipeline`.
4. **Clue Inspection / Forensics / Alibi Telemetry / Cipher Decoding:** Delegate to
   `ForensicsAnalystAgent`.
5. **Suspect Interrogation:** Delegate to `SuspectInterrogatorAgent`.
6. **Formal Accusation / Arrest Warrant:** Delegate to `VerdictJudgeAgent`.
7. **Case Progress / Notebook Check:** Call `list_case_status`.
8. **Error Recovery:** Whenever any tool returns `status='error'`, read and execute its
   `recovery_action` instead of failing silently.

## 4. Non-Negotiable Constraints & Safety Rules
- **Zero Spoilers:** NEVER reveal, hint directly at, or confirm the `sealed_solution` or
  true culprit before `VerdictJudgeAgent` officially closes the case.
- **No Fabricated Forensics:** NEVER invent fingerprint matches, cipher decodings, or alibi
  telemetry results—always rely on `ForensicsAnalystAgent` tool outputs.
- **Privacy First:** Never request or echo personal real-world sensitive data (emails, SSNs,
  phone numbers, or API keys).
"""


def create_mystery_director(
    model: str | None = None,
    enable_mcp: bool | None = None,
    settings: Settings | None = None,
) -> LlmAgent:
    """Assemble the complete multi-agent Interactive AI Mystery Engine hierarchy."""
    cfg = settings or get_settings()
    director_model = select_model_for_role("routing", settings=cfg, override=model)

    case_forge = create_case_forge_pipeline(model=model, settings=cfg)
    forensics_analyst = create_forensics_analyst(
        model=model, enable_mcp=enable_mcp, settings=cfg
    )
    suspect_interrogator = create_suspect_interrogator(model=model, settings=cfg)
    verdict_judge = create_verdict_judge(model=model, settings=cfg)

    return LlmAgent(
        name="MysteryDirector",
        model=director_model,
        description=(
            "Root coordinator for the Interactive AI Mystery Engine. Manages detective "
            "memory, strategic delegation, case initialization, clue forensics, suspect "
            "interrogations, and HITL-confirmed verdicts."
        ),
        instruction=MYSTERY_DIRECTOR_CONSTITUTION,
        tools=[start_new_case, list_case_status, load_memory],
        sub_agents=[
            case_forge,
            forensics_analyst,
            suspect_interrogator,
            verdict_judge,
        ],
        before_model_callback=spoiler_and_safety_guardrail,
        after_model_callback=spoiler_output_self_eval_guardrail,
        before_tool_callback=validate_tool_call_callback,
        after_agent_callback=auto_save_memory_callback,
    )
