"""Primary Google ADK entrypoint exposing `root_agent` and `app`.

Compatible with:
  - `adk web .`
  - `adk run mystery_engine`
  - `adk eval mystery_engine evals/mystery_engine.evalset.json`
  - `adk api_server .`
  - `AgentEvaluator.evaluate(agent_module="mystery_engine.agent", ...)`
  - `python main.py`
  - `python -m mystery_engine.a2a_server`
"""

from __future__ import annotations

from google.adk.apps.app import App, EventsCompactionConfig
from google.adk.plugins.logging_plugin import LoggingPlugin

from mystery_engine.agents.director import create_mystery_director
from mystery_engine.config import Settings, get_settings
from mystery_engine.observability.logging_config import configure_logging
from mystery_engine.observability.plugin import MysteryObservabilityPlugin
from mystery_engine.observability.telemetry import configure_telemetry
from mystery_engine.secrets import bootstrap_runtime_secrets

settings = get_settings()
configure_logging(level=settings.log_level, log_format=settings.log_format)
bootstrap_runtime_secrets(settings)
configure_telemetry(settings)

observability_plugin = MysteryObservabilityPlugin()
logging_plugin = LoggingPlugin()
root_agent = create_mystery_director(
    enable_mcp=settings.enable_mcp_forensics,
    settings=settings,
)


def build_app(custom_settings: Settings | None = None, *, enable_mcp: bool | None = None) -> App:
    """Build a fresh ADK App with event compaction and observability plugins."""
    cfg = custom_settings or get_settings()
    agent_instance = create_mystery_director(
        enable_mcp=cfg.enable_mcp_forensics if enable_mcp is None else enable_mcp,
        settings=cfg,
    )
    plugin_instance = MysteryObservabilityPlugin()
    return App(
        name=cfg.app_name,
        root_agent=agent_instance,
        events_compaction_config=EventsCompactionConfig(
            compaction_interval=cfg.compaction_interval,
            overlap_size=cfg.compaction_overlap,
        ),
        plugins=[plugin_instance, LoggingPlugin()],
    )


app = App(
    name=settings.app_name,
    root_agent=root_agent,
    events_compaction_config=EventsCompactionConfig(
        compaction_interval=settings.compaction_interval,
        overlap_size=settings.compaction_overlap,
    ),
    plugins=[observability_plugin, logging_plugin],
)
