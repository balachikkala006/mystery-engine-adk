"""Strategic Model Router pairing agent workloads with the optimal Gemini tier.

Routes:
- High-reasoning planning, worldbuilding, and lore-critique roles -> `planning_model`
  (default: `gemini-3.8-flash`, or `gemini-3-pro-preview` via `MYSTERY_PLANNING_MODEL`).
- Low-latency interactive routing, tool execution, dialogue, and verdicts -> `fast_model`
  (default: `gemini-3.5-flash` via `MYSTERY_FAST_MODEL`).
"""

from __future__ import annotations

from typing import Literal

from mystery_engine.config import Settings, get_settings

AgentRole = Literal[
    "routing",
    "forensics",
    "dialogue",
    "verdict",
    "worldbuilding",
    "planning",
    "critique",
]

_PLANNING_ROLES: frozenset[str] = frozenset({"worldbuilding", "planning", "critique"})


def select_model_for_role(
    role: AgentRole,
    settings: Settings | None = None,
    override: str | None = None,
) -> str:
    """Return the most appropriate Gemini model ID for the given agent workload."""
    if override:
        return override
    cfg = settings or get_settings()
    if role in _PLANNING_ROLES:
        return cfg.planning_model
    return cfg.fast_model
