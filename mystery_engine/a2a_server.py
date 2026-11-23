"""Agent-to-Agent (A2A) protocol server exposing the Mystery Engine.

Uses Google ADK's `to_a2a` utility to publish an A2A-compliant Starlette/ASGI app
with an automatically generated Agent Card at `/.well-known/agent.json`, enabling
external orchestrators or peer agents to discover and invoke the Mystery Engine.

Run:
    python -m mystery_engine.a2a_server
"""

from __future__ import annotations

import logging

import uvicorn

from mystery_engine.config import get_settings
from mystery_engine.observability.logging_config import configure_logging
from mystery_engine.observability.telemetry import configure_telemetry

logger = logging.getLogger(__name__)


def create_a2a_app(host: str | None = None, port: int | None = None):
    """Wrap the root MysteryDirector agent into an A2A-compliant ASGI application."""
    from google.adk.a2a.utils.agent_to_a2a import to_a2a

    from mystery_engine.agent import root_agent

    settings = get_settings()
    resolved_host = host or settings.host
    resolved_port = port or settings.a2a_port

    logger.info(
        "Exposing '%s' over A2A protocol on %s:%s",
        root_agent.name,
        resolved_host,
        resolved_port,
    )
    return to_a2a(
        root_agent,
        host=resolved_host,
        port=resolved_port,
        protocol="http",
    )


def main() -> None:
    """Start the A2A uvicorn server with structured logging and OTel tracing."""
    settings = get_settings()
    configure_logging(level=settings.log_level, log_format=settings.log_format)
    configure_telemetry(settings)
    a2a_app = create_a2a_app(host=settings.host, port=settings.a2a_port)
    uvicorn.run(a2a_app, host=settings.host, port=settings.a2a_port)


if __name__ == "__main__":
    main()
