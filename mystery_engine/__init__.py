"""ADK package entrypoint so `adk web .` and `adk run mystery_engine` auto-discover `agent`."""

from mystery_engine import agent

__all__ = ["agent"]
